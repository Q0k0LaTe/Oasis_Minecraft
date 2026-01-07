"""
LangChain-powered multi-agent system for orchestrating Minecraft mod generation.

We break the workflow into three cooperating sub-agents:
- InteractiveItemAgent: chats with the user's prompt/history to design items.
- BlockCreationAgent: proposes a companion block with reasonable properties.
- PackagingAgent: plans how the generator should assemble assets and code.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from config import GEMINI_API_KEY, AI_MODEL, AI_TEMPERATURE


def _build_llm(temperature: float = AI_TEMPERATURE) -> ChatGoogleGenerativeAI:
    """Shared helper so every sub-agent uses the same Gemini configuration."""
    return ChatGoogleGenerativeAI(
        google_api_key=GEMINI_API_KEY,
        model=AI_MODEL,
        temperature=temperature,
        max_retries=2,
    )


TOOL_RECIPE_PATTERNS: Dict[str, Dict[str, Any]] = {
    "PICKAXE": {"pattern": ["###", " S ", " S "]},
    "AXE": {
        "pattern": ["##", "S#", " S"],
        "alternates": [["##", "#S", " S"]],
    },
    "SHOVEL": {"pattern": ["#", "S", "S"]},
    "HOE": {
        "pattern": ["##", " S", " S"],
        "alternates": [["##", "S ", "S "]],
    },
    "SWORD": {"pattern": ["#", "#", "S"]},
}


class ItemPropertiesSpec(BaseModel):
    """Rich item configuration that the Java generator can consume."""

    max_stack_size: int = Field(..., ge=1, le=64)
    rarity: str = Field(..., description="COMMON, UNCOMMON, RARE, or EPIC")
    fireproof: bool = Field(..., description="True if lava/fire safe")
    creative_tab: str = Field(..., description="INGREDIENTS, COMBAT, TOOLS, etc.")
    special_ability: str = Field(
        ...,
        description="Short sentence describing how players should use the item.",
    )


class ItemSpec(BaseModel):
    """Interactive output from the item agent."""

    mod_name: str
    mod_id: str
    item_name: str
    item_id: str
    description: str = Field(..., description="Lore-rich description for the user.")
    interaction_hooks: List[str] = Field(
        default_factory=list,
        description="Suggested voice lines or follow-up prompts to stay conversational.",
    )
    clarifying_question: Optional[str] = Field(
        default=None,
        description="Question to ask the user when the concept is ambiguous.",
    )
    follow_up_prompt: Optional[str] = Field(
        default=None,
        description="Prompt snippet the UI can surface for iterative refinement.",
    )
    properties: ItemPropertiesSpec


class BlockPropertiesSpec(BaseModel):
    """Block tuning knobs."""

    material: str = Field(..., description="STONE, METAL, WOOD, GLASS, PLANT, etc.")
    hardness: float = Field(..., ge=0.1, le=100.0)
    resistance: float = Field(..., ge=0.1, le=1200.0)
    luminance: int = Field(..., ge=0, le=15)
    requires_tool: bool = Field(..., description="True if pickaxe/shovel is required.")
    creative_tab: str = Field(..., description="Creative tab for the block item.")
    sound_group: str = Field(..., description="WOOD, METAL, GLASS, STONE, GRASS, etc.")


class BlockSpec(BaseModel):
    """Sub-agent output for block registration."""

    block_name: str
    block_id: str
    description: str
    drop_item_id: str = Field(
        ..., description="Item ID this block should drop when broken."
    )
    gameplay_role: str = Field(
        ...,
        description="Explain how players should use/place the block in the world.",
    )
    properties: BlockPropertiesSpec


class PackagingPlan(BaseModel):
    """High-level plan of how to stitch code + assets together."""

    build_steps: List[str]
    asset_plan: List[str]
    qa_notes: List[str]
    release_summary: str


class ToolPropertiesSpec(BaseModel):
    """Tool balance knobs derived from rarity."""

    attack_damage: float
    attack_speed: float
    durability: int
    mining_level: int
    mining_speed: float
    enchantability: int


class ToolSpec(BaseModel):
    """Lightweight pickaxe definition that the generator can turn into Java."""

    tool_name: str
    tool_id: str
    description: str
    material: str
    properties: ToolPropertiesSpec
    creative_tab: str = "TOOLS"


class InteractiveItemAgent:
    """LangChain chain that keeps track of conversation context while designing items."""

    def __init__(self, llm: Optional[ChatGoogleGenerativeAI] = None):
        self.llm = llm or _build_llm()
        self.parser = PydanticOutputParser(pydantic_object=ItemSpec)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an expert Minecraft designer embedded in a creative chat UI. "
                    "Always keep answers friendly and actionable. "
                    "Respect prior conversation context. Output MUST follow: {format_instructions}",
                ),
                (
                    "human",
                    "Conversation so far:\n{conversation_history}\n\n"
                    "Latest player request:\n{user_prompt}\n\n"
                    "If the player already specified a mod name, enforce it: {mod_name_override}\n",
                ),
            ]
        )

    def run(
        self,
        user_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        mod_name_override: Optional[str] = None,
    ) -> ItemSpec:
        history_text = self._format_history(conversation_history)
        messages = self.prompt.format_messages(
            conversation_history=history_text,
            user_prompt=user_prompt,
            mod_name_override=mod_name_override or "None provided",
            format_instructions=self.parser.get_format_instructions(),
        )
        response = self.llm.invoke(messages)
        item_spec = self.parser.parse(response.content)

        if mod_name_override:
            item_spec.mod_name = mod_name_override
        return item_spec

    @staticmethod
    def _format_history(
        history: Optional[List[Dict[str, str]]]
    ) -> str:
        if not history:
            return "No previous conversation."
        formatted = []
        for turn in history:
            role = turn.get("role", "user").title()
            content = turn.get("content", "")
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)


class BlockCreationAgent:
    """Designs block specs to pair with the crafted item."""

    def __init__(self, llm: Optional[ChatGoogleGenerativeAI] = None):
        self.llm = llm or _build_llm(temperature=0.4)
        self.parser = PydanticOutputParser(pydantic_object=BlockSpec)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You extend mods with exactly one supporting block. "
                    "Use cube-all models (same texture on every face) and stay Fabric 1.21 friendly. "
                    "Output MUST follow: {format_instructions}",
                ),
                (
                    "human",
                    "Player concept:\n{user_prompt}\n\n"
                    "Confirmed item spec:\n"
                    "Name: {item_name}\n"
                    "ID: {item_id}\n"
                    "Rarity: {rarity}\n"
                    "Fireproof: {fireproof}\n"
                    "Describe one perfect block that complements this item.",
                ),
            ]
        )

    def run(self, user_prompt: str, item_spec: ItemSpec) -> BlockSpec:
        messages = self.prompt.format_messages(
            user_prompt=user_prompt,
            item_name=item_spec.item_name,
            item_id=item_spec.item_id,
            rarity=item_spec.properties.rarity,
            fireproof="yes" if item_spec.properties.fireproof else "no",
            format_instructions=self.parser.get_format_instructions(),
        )
        response = self.llm.invoke(messages)
        return self.parser.parse(response.content)


class PackagingAgent:
    """Creates a coordination plan for downstream Python/Gradle steps."""

    def __init__(self, llm: Optional[ChatGoogleGenerativeAI] = None):
        self.llm = llm or _build_llm(temperature=0.3)
        self.parser = PydanticOutputParser(pydantic_object=PackagingPlan)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are the packaging/QA lead. Break work into concise steps for the generator.",
                ),
                (
                    "human",
                    "Item:\n- {item_name} ({item_id})\n"
                    "Block:\n- {block_name} ({block_id})\n"
                    "Player request:\n{user_prompt}\n\n"
                    "Describe build steps, asset needs, and QA notes.\n"
                    "Use short bullet sentences. Format: {format_instructions}",
                ),
            ]
        )

    def run(
        self,
        user_prompt: str,
        item_spec: ItemSpec,
        block_spec: Optional[BlockSpec],
    ) -> PackagingPlan:
        messages = self.prompt.format_messages(
            user_prompt=user_prompt,
            item_name=item_spec.item_name,
            item_id=item_spec.item_id,
            block_name=block_spec.block_name if block_spec else "N/A",
            block_id=block_spec.block_id if block_spec else "N/A",
            format_instructions=self.parser.get_format_instructions(),
        )
        response = self.llm.invoke(messages)
        return self.parser.parse(response.content)


class LangChainModOrchestrator:
    """
    Coordinates all sub-agents and produces a single spec dictionary that is
    backwards-compatible with the previous ModAnalyzer output.
    """

    def __init__(self):
        shared_llm = _build_llm()
        self.item_agent = InteractiveItemAgent(shared_llm)
        self.block_agent = BlockCreationAgent(shared_llm)
        self.packaging_agent = PackagingAgent(shared_llm)

    def run_pipeline(
        self,
        user_prompt: str,
        author_name: Optional[str] = None,
        mod_name_override: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        item_spec = self.item_agent.run(
            user_prompt=user_prompt,
            conversation_history=conversation_history,
            mod_name_override=mod_name_override,
        )
        block_spec = self.block_agent.run(user_prompt=user_prompt, item_spec=item_spec)
        packaging = self.packaging_agent.run(
            user_prompt=user_prompt,
            item_spec=item_spec,
            block_spec=block_spec,
        )

        return self._compose_payload(
            user_prompt=user_prompt,
            author_name=author_name,
            item_spec=item_spec,
            block_spec=block_spec,
            packaging=packaging,
        )

    def _compose_payload(
        self,
        user_prompt: str,
        author_name: Optional[str],
        item_spec: ItemSpec,
        block_spec: Optional[BlockSpec],
        packaging: PackagingPlan,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "modName": item_spec.mod_name,
            "modId": item_spec.mod_id,
            "itemName": item_spec.item_name,
            "itemId": item_spec.item_id,
            "description": user_prompt,
            "author": author_name or "AI Generator",
            "properties": {
                "maxStackSize": item_spec.properties.max_stack_size,
                "rarity": item_spec.properties.rarity,
                "fireproof": item_spec.properties.fireproof,
                "creativeTab": item_spec.properties.creative_tab,
                "specialAbility": item_spec.properties.special_ability,
            },
            "interactive": {
                "hooks": item_spec.interaction_hooks,
                "clarifyingQuestion": item_spec.clarifying_question,
                "followUpPrompt": item_spec.follow_up_prompt,
            },
            "packagingPlan": packaging.dict(),
        }

        if block_spec:
            block_payload = {
                "blockName": block_spec.block_name,
                "blockId": block_spec.block_id,
                "description": block_spec.description,
                "dropItemId": block_spec.drop_item_id,
                "gameplayRole": block_spec.gameplay_role,
                "properties": {
                    "material": block_spec.properties.material,
                    "hardness": block_spec.properties.hardness,
                    "resistance": block_spec.properties.resistance,
                    "luminance": block_spec.properties.luminance,
                    "requiresTool": block_spec.properties.requires_tool,
                    "creativeTab": block_spec.properties.creative_tab,
                    "soundGroup": block_spec.properties.sound_group,
                },
            }
            block_payload["variants"] = self._build_block_variants(
                item_spec=item_spec,
                block_spec=block_spec,
            )
            payload["block"] = block_payload

        tool_spec = self._derive_tool_spec(
            user_prompt=user_prompt,
            item_spec=item_spec,
            block_spec=block_spec,
        )
        if tool_spec:
            payload["tool"] = tool_spec

        return payload

    def _derive_tool_spec(
        self,
        user_prompt: str,
        item_spec: ItemSpec,
        block_spec: Optional[BlockSpec],
    ) -> Dict[str, Any]:
        """Create a deterministic pickaxe spec based on item rarity."""
        rarity = item_spec.properties.rarity.upper()
        tier_settings = {
            "COMMON": dict(
                material="IRON",
                attack_damage=2.0,
                attack_speed=-2.8,
                durability=375,
                mining_level=2,
                mining_speed=6.0,
                enchantability=14,
            ),
            "UNCOMMON": dict(
                material="IRON",
                attack_damage=2.5,
                attack_speed=-2.7,
                durability=420,
                mining_level=2,
                mining_speed=6.5,
                enchantability=16,
            ),
            "RARE": dict(
                material="DIAMOND",
                attack_damage=3.0,
                attack_speed=-2.6,
                durability=1561,
                mining_level=3,
                mining_speed=8.0,
                enchantability=22,
            ),
            "EPIC": dict(
                material="NETHERITE",
                attack_damage=3.5,
                attack_speed=-2.6,
                durability=2031,
                mining_level=4,
                mining_speed=9.0,
                enchantability=24,
            ),
        }
        tier = tier_settings.get(rarity, tier_settings["COMMON"])

        tool_type = self._infer_tool_type(user_prompt, item_spec)
        
        # Swords need higher attack damage than mining tools
        if tool_type == "SWORD":
            tier["attack_damage"] = tier["attack_damage"] * 2.4  # Scale up for combat
            tier["attack_speed"] = max(tier["attack_speed"], -2.4)  # Faster swing
        
        base_name = item_spec.item_name.split()[-1] if item_spec.item_name else "Ruby"
        suffix_lookup = {
            "PICKAXE": "Pickaxe",
            "AXE": "Battle Axe",
            "SHOVEL": "Shovel",
            "HOE": "Hoe",
            "SWORD": "Sword",
        }
        suffix = suffix_lookup.get(tool_type, "Tool")
        tool_name = f"{base_name} {suffix}"
        tool_id = f"{item_spec.item_id}_{suffix.replace(' ', '_').lower()}"
        block_name = block_spec.block_name if block_spec else "rare ores"
        description = f"A {tool_type.lower()} forged from {item_spec.item_name} to conquer {block_name}."
        characteristics = self._describe_tool_characteristics(
            tool_type=tool_type,
            tier=tier,
            item_spec=item_spec,
            block_spec=block_spec,
        )
        forging_recipe = self._build_tool_forging_recipe(
            item_spec=item_spec,
            tool_id=tool_id,
            tool_name=tool_name,
            tool_type=tool_type,
        )

        return {
            "toolName": tool_name,
            "toolId": tool_id,
            "description": description,
            "toolType": tool_type,
            "material": tier["material"],
            "creativeTab": "TOOLS",
            "properties": {
                "attackDamage": tier["attack_damage"],
                "attackSpeed": tier["attack_speed"],
                "durability": tier["durability"],
                "miningLevel": tier["mining_level"],
                "miningSpeed": tier["mining_speed"],
                "enchantability": tier["enchantability"],
            },
            "characteristics": characteristics,
            "forgingRecipe": forging_recipe,
        }

    def _infer_tool_type(self, user_prompt: str, item_spec: ItemSpec) -> str:
        """Pick a tool archetype by scanning the prompt + item description."""
        text = f"{user_prompt} {item_spec.description}".lower()
        heuristics = [
            ("sword", "SWORD"),
            ("blade", "SWORD"),
            ("saber", "SWORD"),
            ("dagger", "SWORD"),
            ("axe", "AXE"),
            ("battleaxe", "AXE"),
            ("hatchet", "AXE"),
            ("hammer", "AXE"),
            ("shovel", "SHOVEL"),
            ("spade", "SHOVEL"),
            ("hoe", "HOE"),
            ("scythe", "HOE"),
            ("pickaxe", "PICKAXE"),
            ("pick", "PICKAXE"),
        ]
        for keyword, tool_type in heuristics:
            if keyword in text:
                return tool_type
        return "PICKAXE"

    def _describe_tool_characteristics(
        self,
        tool_type: str,
        tier: Dict[str, Any],
        item_spec: ItemSpec,
        block_spec: Optional[BlockSpec],
    ) -> List[str]:
        characteristics = [
            f"{tool_type.title()} forged from {item_spec.item_name} essence.",
            f"{int(tier['durability']):,} durability • mining level {tier['mining_level']} • speed {tier['mining_speed']:.1f}",
            f"{tier['attack_damage']:.1f} attack damage • {tier['attack_speed']:.1f} attack speed",
        ]
        ability = item_spec.properties.special_ability
        if ability:
            characteristics.append(f"Synergy: {ability}")
        if block_spec:
            characteristics.append(
                f"Tuned to harvest {block_spec.block_name} for {block_spec.gameplay_role.lower()}."
            )
        else:
            characteristics.append("Balanced for overworld mining expeditions.")
        return characteristics

    def _build_tool_forging_recipe(
        self,
        item_spec: ItemSpec,
        tool_id: str,
        tool_name: str,
        tool_type: str,
    ) -> Dict[str, Any]:
        pattern_info = TOOL_RECIPE_PATTERNS.get(tool_type, TOOL_RECIPE_PATTERNS["PICKAXE"])
        legend = {
            "#": {
                "item": f"{item_spec.mod_id}:{item_spec.item_id}",
                "label": item_spec.item_name,
            },
            "S": {
                "item": "minecraft:stick",
                "label": "Minecraft Stick",
            },
        }
        result = {
            "item": f"{item_spec.mod_id}:{tool_id}",
            "label": tool_name,
            "count": 1,
        }
        return {
            "id": f"{tool_id}_forging",
            "type": "minecraft:crafting_shaped",
            "pattern": pattern_info["pattern"],
            "alternates": pattern_info.get("alternates", []),
            "legend": legend,
            "result": result,
            "notes": f"Arrange {item_spec.item_name} using the {tool_type.lower()} pattern to forge {tool_name}.",
        }

    def _build_block_variants(
        self,
        item_spec: ItemSpec,
        block_spec: BlockSpec,
    ) -> List[Dict[str, Any]]:
        mod_id = item_spec.mod_id
        item_id = item_spec.item_id
        block_id = block_spec.block_id
        block_name = block_spec.block_name
        item_name = item_spec.item_name

        compression_recipe = {
            "id": f"{block_id}_compression",
            "type": "minecraft:crafting_shaped",
            "pattern": ["###", "###", "###"],
            "legend": {
                "#": {
                    "item": f"{mod_id}:{item_id}",
                    "label": item_name,
                }
            },
            "result": {
                "item": f"{mod_id}:{block_id}",
                "label": block_name,
                "count": 1,
            },
            "notes": f"Compress nine {item_name} into a single decorative storage block.",
        }

        crumble_recipe = {
            "id": f"{block_id}_reclaim",
            "type": "minecraft:crafting_shaped",
            "pattern": ["#"],
            "legend": {
                "#": {
                    "item": f"{mod_id}:{block_id}",
                    "label": block_name,
                }
            },
            "result": {
                "item": f"{mod_id}:{item_id}",
                "label": item_name,
                "count": 9,
            },
            "notes": f"Break the block back down into raw {item_name.lower()}.",
        }

        traits_line = (
            f"Hardness {block_spec.properties.hardness:.1f} • Resistance {block_spec.properties.resistance:.1f}"
        )
        luminance = block_spec.properties.luminance
        luminance_trait = f"Luminance {luminance}/15" if luminance else "No inherent glow"

        return [
            {
                "name": f"{block_name} (Storage Form)",
                "description": block_spec.description,
                "traits": [traits_line, luminance_trait],
                "recipe": compression_recipe,
            },
            {
                "name": f"{block_name} (Shard Release)",
                "description": f"Reclaim {item_name} shards without smelting.",
                "traits": ["Single-slot crafting", f"Drops {item_name} x9"],
                "recipe": crumble_recipe,
            },
        ]

