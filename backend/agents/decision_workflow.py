"""
Structured JSON-based decision workflow for mod generation.

This module defines a clear, multi-stage decision pipeline where each stage
produces structured JSON output using Pydantic models. No text parsing required.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
import re

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from config import GEMINI_API_KEY, AI_MODEL, AI_TEMPERATURE


# ============================================================================
# STAGE 1: NAMING & IDENTITY DECISION
# ============================================================================

class NamingDecision(BaseModel):
    """
    First decision stage: Determine all names and IDs.

    This is explicitly separated so we have a single source of truth
    for naming conventions before proceeding with other decisions.
    """
    mod_name: str = Field(
        ...,
        description="Human-readable mod name. Example: 'Ruby Gems Mod', 'Obsidian Tools'",
        min_length=3,
        max_length=50
    )
    mod_id: str = Field(
        ...,
        description="Lowercase mod ID, alphanumeric only, no spaces. Example: 'rubygemsmod', 'obsidiantools'",
        pattern=r'^[a-z0-9]+$',
        min_length=3,
        max_length=30
    )
    item_name: str = Field(
        ...,
        description="Human-readable item name. Example: 'Ruby Gem', 'Obsidian Sword'",
        min_length=2,
        max_length=40
    )
    item_id: str = Field(
        ...,
        description="Lowercase item ID with underscores. Example: 'ruby_gem', 'obsidian_sword'",
        pattern=r'^[a-z0-9_]+$',
        min_length=2,
        max_length=40
    )
    namespace: str = Field(
        default="minecraft",
        description="Namespace for Minecraft registry. Usually 'minecraft' or the mod_id."
    )
    naming_rationale: str = Field(
        ...,
        description="Brief explanation of why these names were chosen based on the user's prompt."
    )

    @field_validator('mod_id', 'item_id')
    @classmethod
    def validate_id_format(cls, v: str, info) -> str:
        """Ensure IDs follow Minecraft conventions."""
        if not v:
            raise ValueError(f"{info.field_name} cannot be empty")

        # Remove any remaining invalid characters
        cleaned = re.sub(r'[^a-z0-9_]', '', v.lower())

        if info.field_name == 'mod_id':
            # Mod IDs should not have underscores
            cleaned = cleaned.replace('_', '')

        if not cleaned:
            raise ValueError(f"{info.field_name} must contain at least one alphanumeric character")

        return cleaned


class NamingAgent:
    """Agent responsible for making all naming decisions."""

    def __init__(self, llm: Optional[ChatGoogleGenerativeAI] = None):
        if llm is None:
            llm = ChatGoogleGenerativeAI(
                google_api_key=GEMINI_API_KEY,
                model=AI_MODEL,
                temperature=0.3,  # Lower temperature for consistent naming
                max_retries=2,
            )

        self.llm = llm
        self.parser = PydanticOutputParser(pydantic_object=NamingDecision)
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a Minecraft mod naming expert. Your ONLY job is to decide names and IDs.\n\n"
                "NAMING RULES:\n"
                "1. mod_name: Should describe the overall theme. Keep it concise and memorable.\n"
                "2. mod_id: Lowercase, no spaces, no special chars. Examples: 'rubymod', 'magicgems'\n"
                "3. item_name: The display name players see in-game. Can be creative.\n"
                "4. item_id: Lowercase with underscores. Examples: 'ruby_gem', 'magic_staff'\n\n"
                "If user specifies a mod name override, you MUST use it exactly for mod_name.\n\n"
                "Output MUST be valid JSON following: {format_instructions}"
            ),
            (
                "human",
                "User request: {user_prompt}\n"
                "Mod name override (use if provided): {mod_name_override}\n\n"
                "Generate naming decisions in JSON format."
            ),
        ])

    def decide(
        self,
        user_prompt: str,
        mod_name_override: Optional[str] = None
    ) -> NamingDecision:
        """
        Make all naming decisions based on user prompt.

        Returns:
            NamingDecision with validated names and IDs
        """
        messages = self.prompt.format_messages(
            user_prompt=user_prompt,
            mod_name_override=mod_name_override or "None provided - create your own",
            format_instructions=self.parser.get_format_instructions(),
        )

        response = self.llm.invoke(messages)
        decision = self.parser.parse(response.content)

        # Apply override if provided
        if mod_name_override:
            decision.mod_name = mod_name_override
            # Regenerate mod_id from override
            decision.mod_id = self._normalize_mod_id(mod_name_override)

        return decision

    @staticmethod
    def _normalize_mod_id(name: str) -> str:
        """Convert any string to a valid mod_id."""
        # Lowercase and remove non-alphanumeric
        normalized = re.sub(r'[^a-z0-9]', '', name.lower())
        return normalized or "custommod"


# ============================================================================
# STAGE 2: PROPERTIES & BALANCE DECISION
# ============================================================================

class PropertiesDecision(BaseModel):
    """
    Second decision stage: Determine gameplay properties and balance.

    This stage focuses on the mechanical aspects of the item.
    """
    max_stack_size: int = Field(
        ...,
        ge=1,
        le=64,
        description="Stack size: 1 for tools/weapons, 16 for rare items, 64 for common items"
    )
    rarity: str = Field(
        ...,
        description="Item rarity tier: COMMON, UNCOMMON, RARE, or EPIC",
        pattern=r'^(COMMON|UNCOMMON|RARE|EPIC)$'
    )
    fireproof: bool = Field(
        ...,
        description="True if item survives in lava/fire (for Netherite-tier or fire-themed items)"
    )
    creative_tab: str = Field(
        ...,
        description="Where item appears in creative inventory: INGREDIENTS, COMBAT, TOOLS, FOOD_AND_DRINK, BUILDING_BLOCKS, FUNCTIONAL"
    )
    special_ability: str = Field(
        ...,
        description="Short description of item's special power or use case. Use 'none' if it's purely decorative."
    )
    gameplay_tags: List[str] = Field(
        default_factory=list,
        description="Minecraft tags that affect item behavior (e.g., 'weapon', 'tool', 'food')"
    )
    balance_reasoning: str = Field(
        ...,
        description="Explanation of why these properties make sense for game balance"
    )


class PropertiesAgent:
    """Agent responsible for deciding item properties and game balance."""

    def __init__(self, llm: Optional[ChatGoogleGenerativeAI] = None):
        if llm is None:
            llm = ChatGoogleGenerativeAI(
                google_api_key=GEMINI_API_KEY,
                model=AI_MODEL,
                temperature=0.4,
                max_retries=2,
            )

        self.llm = llm
        self.parser = PydanticOutputParser(pydantic_object=PropertiesDecision)
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a Minecraft game balance expert. Your job is to decide item properties.\n\n"
                "RARITY GUIDELINES:\n"
                "- COMMON: Basic items, easy to obtain (white text)\n"
                "- UNCOMMON: Slightly special items (yellow text)\n"
                "- RARE: Hard to find, valuable (aqua text)\n"
                "- EPIC: Legendary, extremely powerful (magenta text)\n\n"
                "STACK SIZE RULES:\n"
                "- 1: Tools, weapons, armor (non-stackable)\n"
                "- 16: Valuable materials, rare items\n"
                "- 64: Common materials, basic resources\n\n"
                "CREATIVE TABS:\n"
                "- INGREDIENTS: Crafting materials, gems, resources\n"
                "- COMBAT: Weapons, armor\n"
                "- TOOLS: Mining tools, utilities\n"
                "- FOOD_AND_DRINK: Consumables\n"
                "- BUILDING_BLOCKS: Construction materials\n"
                "- FUNCTIONAL: Redstone, mechanisms\n\n"
                "Output MUST be valid JSON: {format_instructions}"
            ),
            (
                "human",
                "User request: {user_prompt}\n"
                "Item name: {item_name}\n"
                "Item type: {item_type_hint}\n\n"
                "Decide balanced properties for this item."
            ),
        ])

    def decide(
        self,
        user_prompt: str,
        naming: NamingDecision
    ) -> PropertiesDecision:
        """
        Decide item properties based on the prompt and naming.

        Args:
            user_prompt: Original user description
            naming: Previously decided naming information

        Returns:
            PropertiesDecision with validated properties
        """
        # Infer item type from name/prompt for better context
        item_type_hint = self._infer_item_type(user_prompt, naming.item_name)

        messages = self.prompt.format_messages(
            user_prompt=user_prompt,
            item_name=naming.item_name,
            item_type_hint=item_type_hint,
            format_instructions=self.parser.get_format_instructions(),
        )

        response = self.llm.invoke(messages)
        return self.parser.parse(response.content)

    @staticmethod
    def _infer_item_type(prompt: str, item_name: str) -> str:
        """Infer general item category for better context."""
        text = f"{prompt} {item_name}".lower()

        if any(kw in text for kw in ['sword', 'weapon', 'blade', 'bow', 'armor']):
            return "weapon/combat"
        elif any(kw in text for kw in ['pickaxe', 'axe', 'shovel', 'hoe', 'tool']):
            return "tool"
        elif any(kw in text for kw in ['food', 'eat', 'apple', 'bread', 'stew']):
            return "food"
        elif any(kw in text for kw in ['block', 'brick', 'stone', 'wood', 'plank']):
            return "building block"
        elif any(kw in text for kw in ['gem', 'ingot', 'ore', 'shard', 'crystal', 'material']):
            return "crafting material"
        else:
            return "general item"


# ============================================================================
# STAGE 3: UNIFIED DECISION PIPELINE
# ============================================================================

class UnifiedModDecision(BaseModel):
    """
    Complete mod specification combining all decision stages.

    This is the final output that the generator will consume.
    """
    # Stage 1: Naming
    naming: NamingDecision

    # Stage 2: Properties
    properties: PropertiesDecision

    # Metadata
    original_prompt: str = Field(..., description="Original user request for reference")
    author: str = Field(default="AI Generator", description="Mod author name")

    def to_legacy_format(self) -> Dict[str, Any]:
        """
        Convert to the legacy format expected by existing code.

        This ensures backward compatibility with the rest of the system.
        """
        return {
            "modName": self.naming.mod_name,
            "modId": self.naming.mod_id,
            "itemName": self.naming.item_name,
            "itemId": self.naming.item_id,
            "description": self.original_prompt,
            "author": self.author,
            "properties": {
                "maxStackSize": self.properties.max_stack_size,
                "rarity": self.properties.rarity,
                "fireproof": self.properties.fireproof,
                "creativeTab": self.properties.creative_tab,
                "specialAbility": self.properties.special_ability,
            },
        }


class DecisionOrchestrator:
    """
    Orchestrates the multi-stage decision pipeline.

    Each stage produces structured JSON via Pydantic models.
    No text parsing required.
    """

    def __init__(self):
        shared_llm = ChatGoogleGenerativeAI(
            google_api_key=GEMINI_API_KEY,
            model=AI_MODEL,
            temperature=AI_TEMPERATURE,
            max_retries=2,
        )

        self.naming_agent = NamingAgent(shared_llm)
        self.properties_agent = PropertiesAgent(shared_llm)

    def run_decision_pipeline(
        self,
        user_prompt: str,
        author_name: Optional[str] = None,
        mod_name_override: Optional[str] = None,
    ) -> UnifiedModDecision:
        """
        Run the complete decision pipeline.

        Workflow:
        1. NamingAgent decides all names/IDs (with override support)
        2. PropertiesAgent decides gameplay properties
        3. Combine into UnifiedModDecision

        Args:
            user_prompt: User's description of the item
            author_name: Optional author credit
            mod_name_override: Optional explicit mod name from user

        Returns:
            UnifiedModDecision containing all structured decisions
        """
        print(f"[DecisionPipeline] Stage 1: Naming decisions...")
        naming = self.naming_agent.decide(
            user_prompt=user_prompt,
            mod_name_override=mod_name_override
        )
        print(f"[DecisionPipeline] ✓ Naming: mod='{naming.mod_name}' ({naming.mod_id}), item='{naming.item_name}' ({naming.item_id})")

        print(f"[DecisionPipeline] Stage 2: Properties & balance...")
        properties = self.properties_agent.decide(
            user_prompt=user_prompt,
            naming=naming
        )
        print(f"[DecisionPipeline] ✓ Properties: {properties.rarity} rarity, stack={properties.max_stack_size}, tab={properties.creative_tab}")

        decision = UnifiedModDecision(
            naming=naming,
            properties=properties,
            original_prompt=user_prompt,
            author=author_name or "AI Generator"
        )

        print(f"[DecisionPipeline] ✓ Complete decision pipeline finished")
        return decision


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

def example_usage():
    """Example of how to use the decision workflow."""
    orchestrator = DecisionOrchestrator()

    # Example 1: Simple item
    decision = orchestrator.run_decision_pipeline(
        user_prompt="Create a powerful ruby gem that grants fire resistance"
    )
    print("Decision:", decision.model_dump_json(indent=2))
    print("\nLegacy format:", decision.to_legacy_format())

    # Example 2: With mod name override
    decision2 = orchestrator.run_decision_pipeline(
        user_prompt="Create an obsidian sword",
        author_name="Steve",
        mod_name_override="Epic Weapons Pack"
    )
    print("\nDecision 2:", decision2.model_dump_json(indent=2))


if __name__ == "__main__":
    example_usage()
