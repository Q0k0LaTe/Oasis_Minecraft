"""
Orchestrator - Conversation Controller

Responsibilities:
- Translate user prompts into SpecDeltas
- Ask clarifying questions when needed
- Resolve ambiguities using safe defaults
- Maintain conversation context

This component is the ONLY place where LLMs interpret English.
Everything downstream works with structured data.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from config import GEMINI_API_KEY, AI_MODEL, AI_TEMPERATURE
from agents.schemas import ModSpec, SpecDelta, ItemSpec, BlockSpec, ToolSpec, Rarity, CreativeTab


class OrchestratorResponse(BaseModel):
    """Response from the Orchestrator"""
    deltas: List[SpecDelta] = Field(default_factory=list, description="Changes to apply to spec")
    clarifying_questions: List[str] = Field(default_factory=list, description="Questions to ask user")
    reasoning: str = Field(..., description="Why these deltas were produced")
    requires_user_input: bool = Field(False, description="Whether user input is needed before proceeding")


class ConversationContext(BaseModel):
    """Context from previous conversation turns"""
    user_prompts: List[str] = Field(default_factory=list)
    decisions_made: List[str] = Field(default_factory=list)
    ambiguities_resolved: List[str] = Field(default_factory=list)


class Orchestrator:
    """
    Orchestrator - Converts conversations into SpecDeltas

    This is the boundary between human language and structured data.
    """

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            google_api_key=GEMINI_API_KEY,
            model=AI_MODEL,
            temperature=AI_TEMPERATURE,
            max_retries=2,
        )

    def process_prompt(
        self,
        user_prompt: str,
        current_spec: Optional[ModSpec] = None,
        context: Optional[ConversationContext] = None,
        author_name: Optional[str] = None,
        mod_name_override: Optional[str] = None
    ) -> OrchestratorResponse:
        """
        Process user prompt and produce SpecDeltas

        Args:
            user_prompt: What the user wants
            current_spec: Current mod specification (None if starting fresh)
            context: Previous conversation context
            author_name: Mod author name
            mod_name_override: Override for mod name

        Returns:
            OrchestratorResponse with deltas and questions
        """
        context = context or ConversationContext()

        # Determine if this is an initial prompt or iterative refinement
        if current_spec is None:
            return self._handle_initial_prompt(user_prompt, author_name, mod_name_override, context)
        else:
            return self._handle_iterative_prompt(user_prompt, current_spec, context)

    def _handle_initial_prompt(
        self,
        user_prompt: str,
        author_name: Optional[str],
        mod_name_override: Optional[str],
        context: ConversationContext
    ) -> OrchestratorResponse:
        """
        Handle initial mod creation from scratch
        """
        # Parse what the user wants to create
        parsed = self._parse_item_intent(user_prompt)

        # Build deltas for initial spec
        deltas = []

        # Mod metadata
        mod_name = mod_name_override or parsed.get("inferred_mod_name", "Custom Mod")
        deltas.append(SpecDelta(
            operation="add",
            path="mod_name",
            value=mod_name,
            reason="User requested mod creation"
        ))

        if author_name:
            deltas.append(SpecDelta(
                operation="add",
                path="author",
                value=author_name,
                reason="Provided by user"
            ))

        # Add item/block/tool based on what was requested
        item_type = parsed.get("type", "item")

        if item_type == "item":
            item_spec = self._create_item_spec(parsed)
            deltas.append(SpecDelta(
                operation="add",
                path="items[0]",
                value=item_spec.dict(),
                reason=f"User requested: {user_prompt[:50]}..."
            ))
        elif item_type == "block":
            block_spec = self._create_block_spec(parsed)
            deltas.append(SpecDelta(
                operation="add",
                path="blocks[0]",
                value=block_spec.dict(),
                reason=f"User requested: {user_prompt[:50]}..."
            ))
        elif item_type == "tool":
            tool_spec = self._create_tool_spec(parsed)
            deltas.append(SpecDelta(
                operation="add",
                path="tools[0]",
                value=tool_spec.dict(),
                reason=f"User requested: {user_prompt[:50]}..."
            ))

        # Check if clarification needed
        clarifying_questions = []
        if parsed.get("ambiguous_rarity"):
            clarifying_questions.append(
                f"What rarity should {parsed['name']} be? (COMMON, UNCOMMON, RARE, EPIC)"
            )

        return OrchestratorResponse(
            deltas=deltas,
            clarifying_questions=clarifying_questions,
            reasoning=f"Created initial spec for {item_type}: {parsed['name']}",
            requires_user_input=len(clarifying_questions) > 0
        )

    def _handle_iterative_prompt(
        self,
        user_prompt: str,
        current_spec: ModSpec,
        context: ConversationContext
    ) -> OrchestratorResponse:
        """
        Handle modifications to existing spec
        """
        # Determine what user wants to change
        intent = self._parse_modification_intent(user_prompt, current_spec)

        deltas = []

        # Examples of modifications:
        # "make it rarer" -> update rarity
        # "add a pickaxe" -> add new tool
        # "make it glow" -> update luminance

        operation = intent.get("operation")
        target = intent.get("target")

        if operation == "modify_property":
            path = intent.get("path")
            value = intent.get("value")
            deltas.append(SpecDelta(
                operation="update",
                path=path,
                value=value,
                reason=f"User requested: {user_prompt}"
            ))
        elif operation == "add_item":
            new_item = self._create_item_spec(intent)
            deltas.append(SpecDelta(
                operation="add",
                path=f"items[{len(current_spec.items)}]",
                value=new_item.dict(),
                reason=f"User requested additional item: {user_prompt}"
            ))

        return OrchestratorResponse(
            deltas=deltas,
            clarifying_questions=[],
            reasoning=f"Applied modification: {operation}",
            requires_user_input=False
        )

    def _parse_item_intent(self, prompt: str) -> Dict[str, Any]:
        """
        Parse user prompt to extract item intent

        Uses LLM to understand what the user wants to create
        """
        parser = PydanticOutputParser(pydantic_object=ItemIntentParse)

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a Minecraft mod design assistant. Parse the user's request and extract:
- What type of thing they want (item, block, tool)
- The name/description
- Any properties mentioned (rarity, abilities, etc.)
- Inferred creative tab
- Suggested mod name if not a specific item

Be generous in interpretation. If unclear, make reasonable assumptions.
{format_instructions}"""),
            ("user", "{prompt}")
        ])

        chain = prompt_template | self.llm | parser

        try:
            result = chain.invoke({
                "prompt": prompt,
                "format_instructions": parser.get_format_instructions()
            })
            return result.dict()
        except Exception as e:
            # Fallback parsing
            print(f"LLM parsing failed: {e}, using fallback")
            return self._fallback_parse(prompt)

    def _fallback_parse(self, prompt: str) -> Dict[str, Any]:
        """Simple keyword-based parsing as fallback"""
        prompt_lower = prompt.lower()

        # Detect type
        item_type = "item"
        if any(word in prompt_lower for word in ["block", "ore", "stone"]):
            item_type = "block"
        elif any(word in prompt_lower for word in ["pickaxe", "sword", "axe", "shovel", "hoe"]):
            item_type = "tool"

        # Extract name (simple heuristic)
        name = "Custom Item"
        if "called" in prompt_lower:
            name = prompt.split("called", 1)[1].split()[0].strip()

        return {
            "type": item_type,
            "name": name.title(),
            "description": prompt,
            "rarity": "COMMON",
            "inferred_mod_name": f"{name} Mod",
            "creative_tab": "MISC"
        }

    def _parse_modification_intent(self, prompt: str, current_spec: ModSpec) -> Dict[str, Any]:
        """Parse what modification the user wants"""
        prompt_lower = prompt.lower()

        # Simple heuristics for now
        if "rare" in prompt_lower or "epic" in prompt_lower:
            return {
                "operation": "modify_property",
                "target": "items[0]",
                "path": "items[0].rarity",
                "value": "EPIC" if "epic" in prompt_lower else "RARE"
            }
        elif "glow" in prompt_lower or "light" in prompt_lower:
            return {
                "operation": "modify_property",
                "target": "blocks[0]",
                "path": "blocks[0].luminance",
                "value": 15
            }

        return {"operation": "unknown"}

    def _create_item_spec(self, parsed: Dict[str, Any]) -> ItemSpec:
        """Create ItemSpec from parsed intent"""
        return ItemSpec(
            item_name=parsed.get("name", "Custom Item"),
            description=parsed.get("description", "A custom item"),
            rarity=Rarity(parsed.get("rarity", "COMMON")),
            creative_tab=CreativeTab(parsed.get("creative_tab", "MISC")),
            special_ability=parsed.get("special_ability"),
            texture_description=parsed.get("texture_description")
        )

    def _create_block_spec(self, parsed: Dict[str, Any]) -> BlockSpec:
        """Create BlockSpec from parsed intent"""
        return BlockSpec(
            block_name=parsed.get("name", "Custom Block"),
            description=parsed.get("description", "A custom block"),
            creative_tab=CreativeTab.BUILDING_BLOCKS,
            texture_description=parsed.get("texture_description")
        )

    def _create_tool_spec(self, parsed: Dict[str, Any]) -> ToolSpec:
        """Create ToolSpec from parsed intent"""
        tool_type = parsed.get("tool_type", "PICKAXE").upper()
        return ToolSpec(
            tool_name=parsed.get("name", "Custom Tool"),
            tool_type=tool_type,
            description=parsed.get("description", "A custom tool"),
            creative_tab=CreativeTab.TOOLS,
            texture_description=parsed.get("texture_description")
        )


class ItemIntentParse(BaseModel):
    """Parsed intent from user prompt"""
    type: str = Field(..., description="item, block, or tool")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="What it is/does")
    rarity: str = Field("COMMON", description="COMMON, UNCOMMON, RARE, or EPIC")
    creative_tab: str = Field("MISC", description="Creative tab")
    special_ability: Optional[str] = Field(None, description="Special ability if mentioned")
    texture_description: Optional[str] = Field(None, description="How texture should look")
    inferred_mod_name: str = Field(..., description="Suggested mod name")
    ambiguous_rarity: bool = Field(False, description="True if rarity is unclear")
    tool_type: Optional[str] = Field(None, description="PICKAXE, AXE, SWORD, etc.")


__all__ = ["Orchestrator", "OrchestratorResponse", "ConversationContext"]
