"""
AI Agent for analyzing item prompts and deciding mod properties using Gemini
"""
from typing import Dict, Any, Optional
import google.generativeai as genai
from pydantic import BaseModel, Field
import json
import re

from config import (
    GEMINI_API_KEY,
    AI_MODEL,
    AI_TEMPERATURE
)
from .langchain_agents import LangChainModOrchestrator


class ModSpecification(BaseModel):
    """Structured output for mod specification"""
    mod_name: str = Field(description="Display name for the mod (e.g., 'Ruby Gem Mod')")
    mod_id: str = Field(description="Lowercase mod ID with no spaces (e.g., 'rubygemmod')")
    item_name: str = Field(description="Display name for the item (e.g., 'Ruby Gem')")
    item_id: str = Field(description="Lowercase item ID with underscores (e.g., 'ruby_gem')")
    max_stack_size: int = Field(description="Max stack size: 1 for tools/weapons, 16 for rare items, 64 for common", ge=1, le=64)
    rarity: str = Field(description="Rarity: COMMON, UNCOMMON, RARE, or EPIC")
    fireproof: bool = Field(description="Whether the item is fireproof (immune to lava/fire)")
    creative_tab: str = Field(description="Creative tab: INGREDIENTS, COMBAT, TOOLS, FOOD_AND_DRINK, BUILDING_BLOCKS, or FUNCTIONAL")
    reasoning: str = Field(description="Brief explanation of your decisions")


class ModAnalyzerAgent:
    """AI Agent that analyzes prompts and generates mod specifications using Gemini"""

    def __init__(self):
        # Configure Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(AI_MODEL)

        self.orchestrator = LangChainModOrchestrator()

        # System prompt for Gemini
        self.system_prompt = """You are an expert Minecraft mod designer. Your job is to analyze user descriptions of items and decide all the technical details needed to create a Fabric 1.21 mod.

Given a user's description of an item, you must decide:
1. Mod name and ID (based on the item)
2. Item name and ID (extracted from description)
3. Max stack size (1 for tools/weapons, 16 for rare items, 64 for common items)
4. Rarity (COMMON=white, UNCOMMON=yellow, RARE=aqua, EPIC=magenta)
5. Fireproof status (true if related to fire/lava/dragon/nether)
6. Creative tab (where it appears in creative inventory)

Rules for IDs:
- Mod ID: lowercase, no spaces, alphanumeric only (e.g., "rubymod", "magicsword")
- Item ID: lowercase, underscores for spaces (e.g., "ruby_gem", "magic_sword")

Creative Tabs:
- INGREDIENTS: Materials, gems, resources, crafting items
- COMBAT: Swords, weapons, armor
- TOOLS: Tools, staffs, pickaxes, utilities
- FOOD_AND_DRINK: Food, potions, edibles
- BUILDING_BLOCKS: Blocks, construction materials
- FUNCTIONAL: Functional items, mechanisms

Rarity Guidelines:
- COMMON: Basic, everyday items
- UNCOMMON: Special but not rare items
- RARE: Valuable, hard to obtain items
- EPIC: Legendary, extremely powerful items

Max Stack Guidelines:
- 1: Tools, weapons, armor, staffs (non-stackable items)
- 16: Rare/epic materials, special items
- 64: Common materials, basic items

Respond ONLY with valid JSON in this exact format:
{
  "mod_name": "string",
  "mod_id": "string",
  "item_name": "string",
  "item_id": "string",
  "max_stack_size": number,
  "rarity": "COMMON|UNCOMMON|RARE|EPIC",
  "fireproof": boolean,
  "creative_tab": "string",
  "special_ability": "string (short description of item's special ability, or 'none')",
  "reasoning": "string"
}

Be creative but practical. Extract the core concept from the user's description."""

    def analyze(self, user_prompt: str, author_name: str = None, mod_name_override: str = None) -> Dict[str, Any]:
        """
        Analyze user prompt and generate mod specification using the LangChain orchestrator.
        Falls back to the legacy GPT-only flow if LangChain encounters an error.
        """
        try:
            print("Analyzing prompt with LangChain orchestrator")
            return self.orchestrator.run_pipeline(
                user_prompt=user_prompt,
                author_name=author_name,
                mod_name_override=mod_name_override,
            )
        except Exception as orchestrator_error:
            print(f"LangChain orchestrator failed ({orchestrator_error}). Using legacy analyzer.")
            return self._legacy_openai_analyze(user_prompt, author_name, mod_name_override)

    def _legacy_openai_analyze(self, user_prompt: str, author_name: str = None, mod_name_override: str = None) -> Dict[str, Any]:
        """Original Gemini JSON parser retained for resiliency."""
        try:
            print(f"Analyzing with Gemini fallback: {user_prompt}")

            response_text = self._call_gemini(user_prompt)

            print(f"Gemini response: {response_text}")

            # Parse JSON response
            spec_data = json.loads(response_text)

            # Override mod name if provided
            if mod_name_override:
                spec_data['mod_name'] = mod_name_override
                spec_data['mod_id'] = self._generate_id(mod_name_override, allow_underscores=False)

            # Build the result
            result = {
                "modName": spec_data['mod_name'],
                "modId": spec_data['mod_id'],
                "itemName": spec_data['item_name'],
                "itemId": spec_data['item_id'],
                "description": user_prompt,
                "author": author_name or "AI Generator",
                "properties": {
                    "maxStackSize": spec_data['max_stack_size'],
                    "rarity": spec_data['rarity'],
                    "fireproof": spec_data['fireproof'],
                    "creativeTab": spec_data['creative_tab'],
                    "specialAbility": spec_data.get('special_ability', 'none')
                },
                "reasoning": spec_data.get('reasoning', 'Generated by GPT-5.1')
            }

            return result

        except Exception as e:
            print(f"Error analyzing prompt with Gemini fallback: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to simple parsing
            return self._fallback_analysis(user_prompt, author_name, mod_name_override)

    def _call_gemini(self, user_prompt: str) -> str:
        """Call the Gemini API."""
        try:
            # Combine system prompt and user prompt
            full_prompt = f"{self.system_prompt}\n\nUser request: {user_prompt}"

            # Generate content with Gemini
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=AI_TEMPERATURE,
                )
            )

            return response.text
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            raise

    def _generate_id(self, text: str, allow_underscores: bool = True) -> str:
        """Generate a valid ID from text"""
        # Convert to lowercase
        text = text.lower()

        # Remove special characters
        if allow_underscores:
            text = re.sub(r'[^a-z0-9_]', '_', text)
        else:
            text = re.sub(r'[^a-z0-9]', '', text)

        # Remove multiple underscores
        text = re.sub(r'_+', '_', text)

        # Remove leading/trailing underscores
        text = text.strip('_')

        return text or "custom"

    def _fallback_analysis(self, prompt: str, author_name: str = None, mod_name_override: str = None) -> Dict[str, Any]:
        """Fallback analysis if AI fails"""
        # Simple keyword-based analysis
        lower_prompt = prompt.lower()

        # Extract item name (use first few words)
        words = prompt.split()[:3]
        item_name = " ".join(words).title()
        item_id = self._generate_id(item_name)

        # Generate mod name
        if mod_name_override:
            mod_name = mod_name_override
        else:
            mod_name = f"{item_name} Mod"
        mod_id = self._generate_id(mod_name, allow_underscores=False)

        # Determine properties
        rarity = "COMMON"
        if any(word in lower_prompt for word in ["rare", "valuable"]):
            rarity = "RARE"
        elif any(word in lower_prompt for word in ["epic", "legendary"]):
            rarity = "EPIC"
        elif "uncommon" in lower_prompt:
            rarity = "UNCOMMON"

        max_stack = 64
        if any(word in lower_prompt for word in ["sword", "staff", "tool", "weapon"]):
            max_stack = 1
        elif rarity in ["RARE", "EPIC"]:
            max_stack = 16

        fireproof = any(word in lower_prompt for word in ["fire", "lava", "dragon", "nether", "fireproof"])

        creative_tab = "INGREDIENTS"
        if any(word in lower_prompt for word in ["sword", "weapon"]):
            creative_tab = "COMBAT"
        elif any(word in lower_prompt for word in ["tool", "staff"]):
            creative_tab = "TOOLS"
        elif any(word in lower_prompt for word in ["food", "eat", "apple", "potion"]):
            creative_tab = "FOOD_AND_DRINK"

        return {
            "modName": mod_name,
            "modId": mod_id,
            "itemName": item_name,
            "itemId": item_id,
            "description": prompt,
            "author": author_name or "AI Generator",
            "properties": {
                "maxStackSize": max_stack,
                "rarity": rarity,
                "fireproof": fireproof,
                "creativeTab": creative_tab,
                "specialAbility": "none"
            },
            "reasoning": "Fallback analysis used (AI parsing failed)"
        }

