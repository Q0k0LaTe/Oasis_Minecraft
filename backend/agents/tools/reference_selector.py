"""
Reference Selector Agent - Uses LLM to intelligently select reference textures
"""
from pathlib import Path
from typing import List, Dict
import json
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from config import OPENAI_API_KEY


class ReferenceSelection(BaseModel):
    """Selected reference textures with reasoning"""
    selected_textures: List[str] = Field(
        description="List of texture IDs (filenames without .png) to use as references"
    )
    reasoning: str = Field(
        description="Explanation of why these textures were selected"
    )


class ReferenceSelector:
    """Agent that intelligently selects reference textures using LLM reasoning"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=OPENAI_API_KEY,
            temperature=0.3
        )
        self.catalog = self._load_catalog()
        self.textures_dir = Path(__file__).parent / "textures"
        self.parser = PydanticOutputParser(pydantic_object=ReferenceSelection)

    def _load_catalog(self) -> Dict:
        """Load the texture reference catalog"""
        catalog_path = Path(__file__).parent / "texture_catalog.json"
        if catalog_path.exists():
            with open(catalog_path, 'r') as f:
                return json.load(f)
        return {"items": {}, "blocks": {}}

    def _build_catalog_summary(self, for_block: bool = False) -> str:
        """Build a concise summary of available textures for the LLM"""
        catalog_type = "blocks" if for_block else "items"
        textures = self.catalog.get(catalog_type, {})

        # Group by categories for easier browsing
        by_category = {}
        for texture_id, data in textures.items():
            for category in data.get("categories", ["misc"]):
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(texture_id)

        # Build summary
        summary_lines = [f"Available {catalog_type.upper()} ({len(textures)} total):"]
        summary_lines.append("")

        # Sort categories by size
        sorted_categories = sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True)

        # Show top categories with examples
        for category, texture_list in sorted_categories[:15]:  # Top 15 categories
            examples = texture_list[:5]  # Show first 5 examples
            more = f" (+{len(texture_list) - 5} more)" if len(texture_list) > 5 else ""
            summary_lines.append(f"{category} ({len(texture_list)}): {', '.join(examples)}{more}")

        return "\n".join(summary_lines)

    def select_references(
        self,
        item_description: str,
        item_name: str,
        for_block: bool = False,
        max_refs: int = 3
    ) -> List[Path]:
        """
        Use LLM to intelligently select reference textures

        Args:
            item_description: Description of the item to generate
            item_name: Name of the item
            for_block: If True, select block textures; otherwise item textures
            max_refs: Maximum number of references to select

        Returns:
            List of paths to selected reference textures
        """
        catalog_summary = self._build_catalog_summary(for_block=for_block)
        catalog_type = "blocks" if for_block else "items"

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Minecraft texture artist assistant. Your job is to select the most relevant reference textures that will help generate a new texture.

When selecting references, consider:
1. Visual similarity (e.g., swords for swords, gems for gems)
2. Material type (e.g., diamond textures for diamond items, iron for iron, etc.)
3. Style consistency (Minecraft's pixel art aesthetic)
4. Color palette (similar colors or materials)
5. Complexity level (simple items → simple references)

Select {max_refs} textures that will best guide the generation of the requested item.
If no good matches exist, you can select fewer or even zero references.

{format_instructions}"""),
            ("user", """I need to generate a texture for:

Item Name: {item_name}
Description: {item_description}
Type: {item_type}

{catalog_summary}

Please analyze the request and select the most relevant reference textures from the catalog above.
Consider what visual elements, materials, and style would be most helpful as references.

Return your selection as JSON.""")
        ])

        chain = prompt | self.llm | self.parser

        try:
            print(f"🤖 Agent analyzing textures for: {item_name}")
            result = chain.invoke({
                "item_name": item_name,
                "item_description": item_description,
                "item_type": "Block" if for_block else "Item",
                "catalog_summary": catalog_summary,
                "max_refs": max_refs,
                "format_instructions": self.parser.get_format_instructions()
            })

            print(f"💭 Agent reasoning: {result.reasoning}")
            print(f"✓ Selected {len(result.selected_textures)} reference(s)")

            # Convert texture IDs to file paths
            reference_paths = []
            for texture_id in result.selected_textures[:max_refs]:
                # Find the texture in catalog
                texture_data = self.catalog.get(catalog_type, {}).get(texture_id)
                if texture_data:
                    full_path = self.textures_dir.parent / texture_data["path"]
                    if full_path.exists():
                        reference_paths.append(full_path)
                        print(f"  → {texture_id}")
                    else:
                        print(f"  ⚠ Warning: {texture_id} path not found")
                else:
                    print(f"  ⚠ Warning: {texture_id} not in catalog")

            return reference_paths

        except Exception as e:
            print(f"⚠ Agent selection failed: {e}")
            print("  Falling back to no references")
            return []

    def get_texture_info(self, texture_id: str, for_block: bool = False) -> Dict:
        """Get information about a specific texture"""
        catalog_type = "blocks" if for_block else "items"
        return self.catalog.get(catalog_type, {}).get(texture_id, {})
