"""
Asset Generator Tool - Generates all resource files

This tool creates:
- Textures (PNG files)
- Models (JSON files)
- Language files (lang/en_us.json)
- Blockstates
- Recipes
- Loot tables
"""
import json
from pathlib import Path
from typing import Dict, Any, List
import base64
from PIL import Image
from io import BytesIO


def generate_assets(
    workspace_path: Path,
    mod_id: str,
    items: List[Dict[str, Any]] = None,
    blocks: List[Dict[str, Any]] = None,
    tools: List[Dict[str, Any]] = None,
    assets: List[Dict[str, Any]] = None,
    textures: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Generate all resource files (assets and data)

    Args:
        workspace_path: Mod directory path
        mod_id: Mod identifier
        items: List of item specifications from IR
        blocks: List of block specifications from IR
        tools: List of tool specifications from IR
        assets: List of IRAsset specifications
        textures: Optional pre-generated texture map (unused for now)

    Returns:
        Dictionary with paths to generated asset directories
    """
    mod_dir = Path(workspace_path)
    assets_path = mod_dir / "src" / "main" / "resources" / "assets" / mod_id
    data_path = mod_dir / "src" / "main" / "resources" / "data" / mod_id

    items = items or []
    blocks = blocks or []
    tools = tools or []
    assets = assets or []
    textures = textures or {}

    generated_files = []

    # Generate language file
    lang_entries = {}

    # Generate item assets
    for item in items:
        item_id = item.get("item_id", "").split(":")[-1]
        display_name = item.get("display_name", item_id.replace("_", " ").title())

        # Add to lang file
        lang_entries[f"item.{mod_id}.{item_id}"] = display_name

        # Generate item model
        model_path = assets_path / "models" / "item" / f"{item_id}.json"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        model_json = {
            "parent": "minecraft:item/generated",
            "textures": {
                "layer0": f"{mod_id}:item/{item_id}"
            }
        }
        model_path.write_text(json.dumps(model_json, indent=2))
        generated_files.append(str(model_path))

        # Handle texture if provided in assets
        texture_asset = item.get("texture_asset")
        if texture_asset and texture_asset.get("texture_data"):
            texture_path = assets_path / "textures" / "item" / f"{item_id}.png"
            texture_path.parent.mkdir(parents=True, exist_ok=True)
            texture_data = texture_asset["texture_data"]
            if isinstance(texture_data, str):
                # Base64 encoded
                texture_data = base64.b64decode(texture_data)
            texture_path.write_bytes(texture_data)
            generated_files.append(str(texture_path))

    # Generate block assets
    for block in blocks:
        block_id = block.get("block_id", "").split(":")[-1]
        display_name = block.get("display_name", block_id.replace("_", " ").title())

        # Add to lang file
        lang_entries[f"block.{mod_id}.{block_id}"] = display_name

        # Generate blockstate
        blockstate_path = assets_path / "blockstates" / f"{block_id}.json"
        blockstate_path.parent.mkdir(parents=True, exist_ok=True)
        blockstate_json = {
            "variants": {
                "": {
                    "model": f"{mod_id}:block/{block_id}"
                }
            }
        }
        blockstate_path.write_text(json.dumps(blockstate_json, indent=2))
        generated_files.append(str(blockstate_path))

        # Generate block model
        block_model_path = assets_path / "models" / "block" / f"{block_id}.json"
        block_model_path.parent.mkdir(parents=True, exist_ok=True)
        block_model_json = {
            "parent": "minecraft:block/cube_all",
            "textures": {
                "all": f"{mod_id}:block/{block_id}"
            }
        }
        block_model_path.write_text(json.dumps(block_model_json, indent=2))
        generated_files.append(str(block_model_path))

        # Generate block item model
        item_model_path = assets_path / "models" / "item" / f"{block_id}.json"
        item_model_path.parent.mkdir(parents=True, exist_ok=True)
        item_model_json = {
            "parent": f"{mod_id}:block/{block_id}"
        }
        item_model_path.write_text(json.dumps(item_model_json, indent=2))
        generated_files.append(str(item_model_path))

        # Handle texture
        texture_asset = block.get("texture_asset")
        if texture_asset and texture_asset.get("texture_data"):
            texture_path = assets_path / "textures" / "block" / f"{block_id}.png"
            texture_path.parent.mkdir(parents=True, exist_ok=True)
            texture_data = texture_asset["texture_data"]
            if isinstance(texture_data, str):
                texture_data = base64.b64decode(texture_data)
            texture_path.write_bytes(texture_data)
            generated_files.append(str(texture_path))

        # Generate loot table
        drop_item = block.get("drop_item_id", f"{mod_id}:{block_id}")
        loot_table_path = data_path / "loot_table" / "blocks" / f"{block_id}.json"
        loot_table_path.parent.mkdir(parents=True, exist_ok=True)
        loot_table_json = {
            "type": "minecraft:block",
            "pools": [{
                "rolls": 1,
                "entries": [{
                    "type": "minecraft:item",
                    "name": drop_item
                }],
                "conditions": [{
                    "condition": "minecraft:survives_explosion"
                }]
            }]
        }
        loot_table_path.write_text(json.dumps(loot_table_json, indent=2))
        generated_files.append(str(loot_table_path))

    # Generate tool assets (similar to items)
    for tool in tools:
        tool_id = tool.get("tool_id", "").split(":")[-1]
        display_name = tool.get("display_name", tool_id.replace("_", " ").title())

        lang_entries[f"item.{mod_id}.{tool_id}"] = display_name

        # Generate model
        model_path = assets_path / "models" / "item" / f"{tool_id}.json"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        model_json = {
            "parent": "minecraft:item/handheld",
            "textures": {
                "layer0": f"{mod_id}:item/{tool_id}"
            }
        }
        model_path.write_text(json.dumps(model_json, indent=2))
        generated_files.append(str(model_path))

        # Handle texture
        texture_asset = tool.get("texture_asset")
        if texture_asset and texture_asset.get("texture_data"):
            texture_path = assets_path / "textures" / "item" / f"{tool_id}.png"
            texture_path.parent.mkdir(parents=True, exist_ok=True)
            texture_data = texture_asset["texture_data"]
            if isinstance(texture_data, str):
                texture_data = base64.b64decode(texture_data)
            texture_path.write_bytes(texture_data)
            generated_files.append(str(texture_path))

    # Write language file
    lang_path = assets_path / "lang" / "en_us.json"
    lang_path.parent.mkdir(parents=True, exist_ok=True)
    lang_path.write_text(json.dumps(lang_entries, indent=2))
    generated_files.append(str(lang_path))

    # Generate pack.mcmeta for resource pack
    pack_mcmeta_path = mod_dir / "src" / "main" / "resources" / "pack.mcmeta"
    pack_mcmeta = {
        "pack": {
            "description": "Resources for " + mod_id,
            "pack_format": 34
        }
    }
    pack_mcmeta_path.write_text(json.dumps(pack_mcmeta, indent=2))
    generated_files.append(str(pack_mcmeta_path))

    return {
        "status": "success",
        "assets_path": str(assets_path),
        "data_path": str(data_path),
        "files_generated": len(generated_files),
        "generated_files": generated_files
    }


__all__ = ["generate_assets"]
