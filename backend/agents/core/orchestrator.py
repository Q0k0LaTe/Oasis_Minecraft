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

from config import GEMINI_API_KEY, AI_MODEL, AI_TEMPERATURE, AI_REQUEST_TIMEOUT, AI_MAX_RETRIES
from agents.schemas import (
    ModSpec,
    SpecDelta,
    ItemSpec,
    BlockSpec,
    ToolSpec,
    Rarity,
    CreativeTab,
    normalize_creative_tab,
)


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
            max_retries=AI_MAX_RETRIES,
            request_timeout=AI_REQUEST_TIMEOUT,
            transport="rest",  # Use REST API instead of gRPC to avoid proxy issues
        )

    @staticmethod
    def _format_reason(user_prompt: str, max_len: int = 100) -> str:
        """Format reason string with consistent truncation"""
        if len(user_prompt) <= max_len:
            return f"User requested: {user_prompt}"
        return f"User requested: {user_prompt[:max_len]}..."

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

        # Process all items/blocks/tools from parsed result
        items_list = parsed.get("items", [])
        clarifying_questions = []
        created_names = []

        # Counters for array indices
        item_idx = 0
        block_idx = 0
        tool_idx = 0

        for parsed_item in items_list:
            item_type = parsed_item.get("type", "item")
            item_name = parsed_item.get("name", "Unknown")
            created_names.append(item_name)

            if item_type == "item":
                item_spec = self._create_item_spec(parsed_item)
                deltas.append(SpecDelta(
                    operation="add",
                    path=f"items[{item_idx}]",
                    value=item_spec.dict(),
                    reason=self._format_reason(user_prompt)
                ))
                item_idx += 1
            elif item_type == "block":
                block_spec = self._create_block_spec(parsed_item)
                deltas.append(SpecDelta(
                    operation="add",
                    path=f"blocks[{block_idx}]",
                    value=block_spec.dict(),
                    reason=self._format_reason(user_prompt)
                ))
                block_idx += 1
            elif item_type == "tool":
                tool_spec = self._create_tool_spec(parsed_item)
                deltas.append(SpecDelta(
                    operation="add",
                    path=f"tools[{tool_idx}]",
                    value=tool_spec.dict(),
                    reason=self._format_reason(user_prompt)
                ))
                tool_idx += 1

            # Check if clarification needed for this item
            if parsed_item.get("ambiguous_rarity"):
                clarifying_questions.append(
                    f"What rarity should {item_name} be? (COMMON, UNCOMMON, RARE, EPIC)"
                )

        # Generate reasoning summary
        if len(created_names) == 1:
            reasoning = f"Created initial spec with: {created_names[0]}"
        else:
            reasoning = f"Created initial spec with {len(created_names)} items: {', '.join(created_names)}"

        return OrchestratorResponse(
            deltas=deltas,
            clarifying_questions=clarifying_questions,
            reasoning=reasoning,
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
        import logging
        logger = logging.getLogger(__name__)
        
        # Determine what user wants to change
        intent = self._parse_modification_intent(user_prompt, current_spec)
        logger.info(f"[Orchestrator] Parsed intent: {intent}")

        deltas = []
        clarifying_questions = []

        # Examples of modifications:
        # "make it rarer" -> update rarity
        # "add a pickaxe" -> add new tool
        # "make it glow" -> update luminance

        operation = intent.get("operation")
        target = intent.get("target")
        
        logger.info(f"[Orchestrator] Operation: {operation}, Target: {target}")

        if operation == "modify_property":
            path = intent.get("path")
            value = intent.get("value")
            if path and value is not None:
                deltas.append(SpecDelta(
                    operation="update",
                    path=path,
                    value=value,
                    reason=self._format_reason(user_prompt)
                ))
            else:
                logger.warning(f"[Orchestrator] Invalid modify_property: path={path}, value={value}")
                
        elif operation == "add_item":
            # BUG FIX: Use new_item_data, not intent directly
            new_item_data = intent.get("new_item_data", {})
            logger.info(f"[Orchestrator] Adding item with data: {new_item_data}")
            new_item = self._create_item_spec(new_item_data)
            deltas.append(SpecDelta(
                operation="add",
                path=f"items[{len(current_spec.items)}]",
                value=new_item.dict(),
                reason=self._format_reason(user_prompt)
            ))
            
        elif operation == "add_block":
            new_block_data = intent.get("new_item_data", {})
            logger.info(f"[Orchestrator] Adding block with data: {new_block_data}")
            new_block = self._create_block_spec(new_block_data)
            deltas.append(SpecDelta(
                operation="add",
                path=f"blocks[{len(current_spec.blocks)}]",
                value=new_block.dict(),
                reason=self._format_reason(user_prompt)
            ))
            
        elif operation == "add_tool":
            new_tool_data = intent.get("new_item_data", {})
            logger.info(f"[Orchestrator] Adding tool with data: {new_tool_data}")
            new_tool = self._create_tool_spec(new_tool_data)
            deltas.append(SpecDelta(
                operation="add",
                path=f"tools[{len(current_spec.tools)}]",
                value=new_tool.dict(),
                reason=self._format_reason(user_prompt)
            ))
            
        elif operation == "unknown":
            logger.warning(f"[Orchestrator] Unknown operation for prompt: {user_prompt}")
            clarifying_questions.append(
                "I'm not sure what you'd like me to do. Could you be more specific? "
                "For example: 'add a ruby sword' or 'make the first item rarer'"
            )
        
        reasoning = f"Applied modification: {operation}" if deltas else f"Could not apply: {operation}"
        logger.info(f"[Orchestrator] Generated {len(deltas)} deltas, {len(clarifying_questions)} questions")

        return OrchestratorResponse(
            deltas=deltas,
            clarifying_questions=clarifying_questions,
            reasoning=reasoning,
            requires_user_input=len(clarifying_questions) > 0
        )

    def _parse_item_intent(self, prompt: str) -> Dict[str, Any]:
        """
        Parse user prompt to extract item intent

        Uses LLM to understand what the user wants to create
        """
        parser = PydanticOutputParser(pydantic_object=ItemIntentParse)

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a Minecraft mod design assistant. Parse the user's request and extract:
- What type of things they want (item, block, tool) - can be MULTIPLE items
- The name/description for each item
- Any properties mentioned (rarity, abilities, etc.)
- Inferred creative tab for each
- Suggested mod name

IMPORTANT: If the user asks for multiple items (e.g., "a sword and shield", "ruby ore and ruby ingot"),
return ALL of them in the items list. Be generous in interpretation. If unclear, make reasonable assumptions.
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
            # Fallback to safe defaults if LLM parsing fails
            print(f"Warning: LLM parsing failed, using fallback. Error: {e}")
            return {
                "items": [{
                    "type": "item",
                    "name": prompt[:30] if len(prompt) < 30 else prompt[:30] + "...",
                    "description": prompt,
                    "rarity": "COMMON",
                    "creative_tab": "MISC",
                    "special_ability": None,
                    "texture_description": None,
                    "ambiguous_rarity": False,
                    "tool_type": None
                }],
                "inferred_mod_name": "Custom Mod"
            }

    def _parse_modification_intent(self, prompt: str, current_spec: ModSpec) -> Dict[str, Any]:
        """
        Parse what modification the user wants using LLM

        Args:
            prompt: User's modification request
            current_spec: Current mod specification for context

        Returns:
            Dictionary with operation details
        """
        import logging
        logger = logging.getLogger(__name__)
        
        parser = PydanticOutputParser(pydantic_object=ModificationIntentParse)

        # Build context about current spec
        spec_context = f"""Current mod specification:
- Mod name: {current_spec.mod_name}
- Items: {len(current_spec.items)} items ({', '.join([item.item_name for item in current_spec.items[:3]])}{"..." if len(current_spec.items) > 3 else ""})
- Blocks: {len(current_spec.blocks)} blocks ({', '.join([block.block_name for block in current_spec.blocks[:3]])}{"..." if len(current_spec.blocks) > 3 else ""})
- Tools: {len(current_spec.tools)} tools ({', '.join([tool.tool_name for tool in current_spec.tools[:3]])}{"..." if len(current_spec.tools) > 3 else ""})"""

        logger.info(f"[Orchestrator] _parse_modification_intent called with prompt: {prompt}")
        logger.info(f"[Orchestrator] Spec context: {spec_context}")

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a Minecraft mod modification assistant. Parse the user's modification request and determine:
- What operation they want (modify_property, add_item, add_block, add_tool, remove_item, remove_block, remove_tool)
- What target they're referring to (by name or index, e.g., "first item", "ruby sword")
- What property to change (if modifying)
- What value to set (if modifying)
- What to add (if adding new item/block/tool)

For ADD operations, you MUST fill in the new_item field with:
- type: "item", "block", or "tool"
- name: A descriptive name based on the user's request
- description: What the item does or is
- rarity: COMMON, UNCOMMON, RARE, or EPIC
- creative_tab: Appropriate tab
- special_ability: Any mentioned abilities
- texture_description: How it should look

Examples:
- "add a ruby that grows in dark" -> operation=add_item, new_item={{type="item", name="Dark Ruby", description="A magical ruby that grows in darkness", rarity="RARE", special_ability="Grows in dark environments"}}
- "make it rarer" -> modify rarity property of most recent item
- "add a pickaxe" -> add new tool with appropriate properties

{format_instructions}"""),
            ("user", "Context:\n{spec_context}\n\nUser request: {prompt}")
        ])

        chain = prompt_template | self.llm | parser

        try:
            result = chain.invoke({
                "spec_context": spec_context,
                "prompt": prompt,
                "format_instructions": parser.get_format_instructions()
            })
            parsed = result.dict()
            logger.info(f"[Orchestrator] LLM parsed result: {parsed}")

            # Convert parsed result to the format expected by _handle_iterative_prompt
            intent = {"operation": parsed["operation"]}

            if parsed["operation"] == "modify_property":
                # Build path from target info
                target_type = parsed.get("target_type", "items")
                target_index = parsed.get("target_index", 0)
                property_name = parsed.get("property_name", "rarity")

                intent["path"] = f"{target_type}[{target_index}].{property_name}"
                intent["value"] = parsed.get("property_value")
                intent["target"] = parsed.get("target")

            elif parsed["operation"] in ["add_item", "add_block", "add_tool"]:
                new_item = parsed.get("new_item")
                logger.info(f"[Orchestrator] new_item from LLM: {new_item}")
                # Ensure we have a dict, handle both dict and None
                intent["new_item_data"] = new_item if new_item else {}
                logger.info(f"[Orchestrator] new_item_data: {intent['new_item_data']}")

            logger.info(f"[Orchestrator] Final intent: {intent}")
            return intent

        except Exception as e:
            # Fallback to simple heuristics
            logger.error(f"[Orchestrator] LLM modification parsing failed: {e}", exc_info=True)
            prompt_lower = prompt.lower()

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
            creative_tab=normalize_creative_tab(parsed.get("creative_tab", "MISC"), CreativeTab.MISC),
            special_ability=parsed.get("special_ability"),
            texture_description=parsed.get("texture_description")
        )

    def _create_block_spec(self, parsed: Dict[str, Any]) -> BlockSpec:
        """Create BlockSpec from parsed intent"""
        return BlockSpec(
            block_name=parsed.get("name", "Custom Block"),
            description=parsed.get("description", "A custom block"),
            creative_tab=normalize_creative_tab(parsed.get("creative_tab"), CreativeTab.BUILDING_BLOCKS),
            texture_description=parsed.get("texture_description")
        )

    def _create_tool_spec(self, parsed: Dict[str, Any]) -> ToolSpec:
        """Create ToolSpec from parsed intent"""
        tool_type = parsed.get("tool_type", "PICKAXE").upper()
        return ToolSpec(
            tool_name=parsed.get("name", "Custom Tool"),
            tool_type=tool_type,
            description=parsed.get("description", "A custom tool"),
            creative_tab=normalize_creative_tab(parsed.get("creative_tab"), CreativeTab.TOOLS),
            texture_description=parsed.get("texture_description")
        )


class ParsedItem(BaseModel):
    """A single parsed item/block/tool"""
    type: str = Field(..., description="item, block, or tool")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="What it is/does")
    rarity: str = Field("COMMON", description="COMMON, UNCOMMON, RARE, or EPIC")
    creative_tab: str = Field("MISC", description="Creative tab")
    special_ability: Optional[str] = Field(None, description="Special ability if mentioned")
    texture_description: Optional[str] = Field(None, description="How texture should look")
    ambiguous_rarity: bool = Field(False, description="True if rarity is unclear")
    tool_type: Optional[str] = Field(None, description="PICKAXE, AXE, SWORD, etc.")


class ItemIntentParse(BaseModel):
    """Parsed intent from user prompt - supports multiple items"""
    items: List[ParsedItem] = Field(..., description="List of items/blocks/tools to create")
    inferred_mod_name: str = Field(..., description="Suggested mod name")


class ModificationIntentParse(BaseModel):
    """Parsed modification intent for existing spec"""
    operation: str = Field(..., description="modify_property, add_item, add_block, add_tool, remove_item, remove_block, remove_tool")
    target: Optional[str] = Field(None, description="What to modify (e.g., 'first item', 'ruby sword', 'all blocks')")
    target_index: Optional[int] = Field(None, description="Index of item/block/tool to modify (0-based)")
    target_type: Optional[str] = Field(None, description="items, blocks, or tools")
    property_name: Optional[str] = Field(None, description="Property to modify (e.g., 'rarity', 'luminance', 'hardness')")
    property_value: Optional[Any] = Field(None, description="New value for the property")
    new_item: Optional[ParsedItem] = Field(None, description="New item/block/tool to add (for add operations)")
    reasoning: str = Field(..., description="Why this interpretation was chosen")


__all__ = ["Orchestrator", "OrchestratorResponse", "ConversationContext"]
