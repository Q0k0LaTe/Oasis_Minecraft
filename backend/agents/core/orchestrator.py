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
        Handle modifications to existing spec - supports batch operations
        """
        import logging
        logger = logging.getLogger(__name__)

        # Determine what user wants to change
        intent = self._parse_modification_intent(user_prompt, current_spec)
        logger.info(f"[Orchestrator] Parsed intent: {intent}")

        deltas = []
        clarifying_questions = []

        # Get all operations (support both single and batch)
        ops = intent.get("operations", [])
        if not ops and intent.get("operation"):
            # Backward compat: single operation - convert to list format
            ops = [intent]

        logger.info(f"[Orchestrator] Processing {len(ops)} operations")

        # Track indices for add operations (to handle multiple adds in same batch)
        item_add_count = 0
        block_add_count = 0
        tool_add_count = 0

        for op in ops:
            operation = op.get("operation")
            target = op.get("target")

            logger.info(f"[Orchestrator] Processing operation: {operation}, Target: {target}, Full op: {op}")

            if operation == "modify_property":
                path = op.get("path")
                value = op.get("value")
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
                new_item_data = op.get("new_item_data") or op.get("new_item") or {}
                if isinstance(new_item_data, dict):
                    item_dict = new_item_data
                else:
                    item_dict = new_item_data.dict() if hasattr(new_item_data, 'dict') else {}
                logger.info(f"[Orchestrator] Adding item with data: {item_dict}")
                new_item = self._create_item_spec(item_dict)
                deltas.append(SpecDelta(
                    operation="add",
                    path=f"items[{len(current_spec.items) + item_add_count}]",
                    value=new_item.dict(),
                    reason=self._format_reason(user_prompt)
                ))
                item_add_count += 1

            elif operation == "add_block":
                new_block_data = op.get("new_item_data") or op.get("new_item") or {}
                if isinstance(new_block_data, dict):
                    block_dict = new_block_data
                else:
                    block_dict = new_block_data.dict() if hasattr(new_block_data, 'dict') else {}
                logger.info(f"[Orchestrator] Adding block with data: {block_dict}")
                new_block = self._create_block_spec(block_dict)
                deltas.append(SpecDelta(
                    operation="add",
                    path=f"blocks[{len(current_spec.blocks) + block_add_count}]",
                    value=new_block.dict(),
                    reason=self._format_reason(user_prompt)
                ))
                block_add_count += 1

            elif operation == "add_tool":
                new_tool_data = op.get("new_item_data") or op.get("new_item") or {}
                if isinstance(new_tool_data, dict):
                    tool_dict = new_tool_data
                else:
                    tool_dict = new_tool_data.dict() if hasattr(new_tool_data, 'dict') else {}
                logger.info(f"[Orchestrator] Adding tool with data: {tool_dict}")
                new_tool = self._create_tool_spec(tool_dict)
                deltas.append(SpecDelta(
                    operation="add",
                    path=f"tools[{len(current_spec.tools) + tool_add_count}]",
                    value=new_tool.dict(),
                    reason=self._format_reason(user_prompt)
                ))
                tool_add_count += 1

            elif operation == "remove_item":
                target_idx = self._resolve_target_index(op, current_spec.items, "item")
                if target_idx is not None:
                    item_name = current_spec.items[target_idx].item_name
                    deltas.append(SpecDelta(
                        operation="remove",
                        path=f"items[{target_idx}]",
                        value={"name": item_name, "type": "item"},
                        reason=f"User requested: delete {item_name}"
                    ))
                else:
                    item_names = [i.item_name for i in current_spec.items]
                    clarifying_questions.append(f"Which item should I remove? Current items: {item_names}")

            elif operation == "remove_block":
                target_idx = self._resolve_target_index(op, current_spec.blocks, "block")
                if target_idx is not None:
                    block_name = current_spec.blocks[target_idx].block_name
                    deltas.append(SpecDelta(
                        operation="remove",
                        path=f"blocks[{target_idx}]",
                        value={"name": block_name, "type": "block"},
                        reason=f"User requested: delete {block_name}"
                    ))
                else:
                    block_names = [b.block_name for b in current_spec.blocks]
                    clarifying_questions.append(f"Which block should I remove? Current blocks: {block_names}")

            elif operation == "remove_tool":
                target_idx = self._resolve_target_index(op, current_spec.tools, "tool")
                if target_idx is not None:
                    tool_name = current_spec.tools[target_idx].tool_name
                    deltas.append(SpecDelta(
                        operation="remove",
                        path=f"tools[{target_idx}]",
                        value={"name": tool_name, "type": "tool"},
                        reason=f"User requested: delete {tool_name}"
                    ))
                else:
                    tool_names = [t.tool_name for t in current_spec.tools]
                    clarifying_questions.append(f"Which tool should I remove? Current tools: {tool_names}")

            elif operation == "unknown":
                logger.warning(f"[Orchestrator] Unknown operation for prompt: {user_prompt}")
                clarifying_questions.append(
                    "I'm not sure what you'd like me to do. Could you be more specific? "
                    "For example: 'add a ruby sword' or 'make the first item rarer'"
                )

        # Sort remove deltas by index (highest first) to prevent index shifting issues
        # when deleting multiple items from the same array
        import re
        def get_remove_index(delta):
            if delta.operation != "remove":
                return -1
            match = re.search(r'\[(\d+)\]', delta.path)
            return int(match.group(1)) if match else -1

        # Separate remove deltas by type and sort each group
        remove_deltas = [d for d in deltas if d.operation == "remove"]
        other_deltas = [d for d in deltas if d.operation != "remove"]

        # Sort remove deltas by path type first, then by index descending
        remove_deltas.sort(key=lambda d: (d.path.split('[')[0], -get_remove_index(d)))

        # Recombine: other deltas first, then sorted remove deltas
        deltas = other_deltas + remove_deltas

        # Build reasoning summary
        if len(ops) > 1:
            op_types = [op.get("operation", "unknown") for op in ops]
            reasoning = f"Applied {len(deltas)} modifications: {', '.join(op_types)}"
        elif deltas:
            reasoning = f"Applied modification: {ops[0].get('operation') if ops else 'unknown'}"
        else:
            reasoning = f"Could not apply: {ops[0].get('operation') if ops else 'unknown'}"

        logger.info(f"[Orchestrator] Generated {len(deltas)} deltas, {len(clarifying_questions)} questions")

        return OrchestratorResponse(
            deltas=deltas,
            clarifying_questions=clarifying_questions,
            reasoning=reasoning,
            requires_user_input=len(clarifying_questions) > 0
        )

    def _resolve_target_index(self, op: dict, items_list: list, type_name: str) -> Optional[int]:
        """
        Resolve target to an index - by index or by name search

        Args:
            op: Operation dict with target/target_index
            items_list: List of items to search
            type_name: 'item', 'block', or 'tool' (for name attribute lookup)

        Returns:
            Index if found, None otherwise
        """
        # If explicit index provided
        if op.get("target_index") is not None:
            idx = op["target_index"]
            if 0 <= idx < len(items_list):
                return idx

        # Search by name - check both directions (target in name, or name in target)
        target = op.get("target", "")
        if target:
            target_lower = target.lower()
            name_attr = f"{type_name}_name"
            for idx, item in enumerate(items_list):
                item_name = getattr(item, name_attr, "") or ""
                item_name_lower = item_name.lower()
                # Check if target contains item name or item name contains target
                if target_lower in item_name_lower or item_name_lower in target_lower:
                    return idx

            # Try matching individual words from target against item names
            target_words = [w for w in target_lower.split() if len(w) > 2 and w not in ('the', 'and', 'delete', 'remove', 'first', 'second', 'item', 'block', 'tool')]
            for idx, item in enumerate(items_list):
                item_name = getattr(item, name_attr, "") or ""
                item_name_lower = item_name.lower()
                for word in target_words:
                    if word in item_name_lower:
                        return idx

        # If only one item exists, use it
        if len(items_list) == 1:
            return 0

        return None

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

IMPORTANT: If the user requests MULTIPLE additions or deletions (e.g., "add a sword and a shield", "delete the ruby and the emerald"),
return MULTIPLE operations in the operations list - one for each item.

For ADD operations, you MUST fill in the new_item field with:
- type: "item", "block", or "tool"
- name: A descriptive name based on the user's request
- description: What the item does or is
- rarity: COMMON, UNCOMMON, RARE, or EPIC
- creative_tab: Appropriate tab
- special_ability: Any mentioned abilities
- texture_description: How it should look

For REMOVE operations, you MUST fill in:
- target: The name or description of the item to remove (e.g., "ruby sword", "first item")
- target_index: The index if identifiable (0-based)
- target_type: "items", "blocks", or "tools"

Examples:
- "add a ruby that grows in dark" -> operation=add_item, new_item={{type="item", name="Dark Ruby", description="A magical ruby that grows in darkness", rarity="RARE", special_ability="Grows in dark environments"}}
- "add a sword and a shield" -> operations=[{{operation="add_item", new_item={{type="item", name="Sword", ...}}}}, {{operation="add_item", new_item={{type="item", name="Shield", ...}}}}]
- "make it rarer" -> modify rarity property of most recent item
- "add a pickaxe" -> add new tool with appropriate properties
- "delete the ruby sword" -> operation=remove_item, target="ruby sword", target_type="items"
- "remove the first block" -> operation=remove_block, target="first block", target_index=0, target_type="blocks"

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

            # Check if we have multiple operations
            operations_list = parsed.get("operations", [])
            if operations_list:
                # Batch mode - convert SingleOperation models to dicts
                intent = {"operations": []}
                for op in operations_list:
                    op_dict = op if isinstance(op, dict) else op
                    converted_op = {
                        "operation": op_dict.get("operation"),
                        "target": op_dict.get("target"),
                        "target_index": op_dict.get("target_index"),
                        "target_type": op_dict.get("target_type"),
                    }
                    # Handle new_item for add operations
                    if op_dict.get("operation") in ["add_item", "add_block", "add_tool"]:
                        new_item = op_dict.get("new_item")
                        converted_op["new_item"] = new_item if new_item else {}
                    intent["operations"].append(converted_op)
                logger.info(f"[Orchestrator] Batch intent with {len(intent['operations'])} operations")
                return intent

            # Single operation mode (backward compat)
            operation = parsed["operation"]
            intent = {"operation": operation}

            logger.info(f"[Orchestrator] Single operation mode: operation='{operation}', type={type(operation)}")

            if operation == "modify_property":
                # Build path from target info
                target_type = parsed.get("target_type", "items")
                target_index = parsed.get("target_index", 0)
                property_name = parsed.get("property_name", "rarity")

                intent["path"] = f"{target_type}[{target_index}].{property_name}"
                intent["value"] = parsed.get("property_value")
                intent["target"] = parsed.get("target")

            elif operation in ["add_item", "add_block", "add_tool"]:
                new_item = parsed.get("new_item")
                logger.info(f"[Orchestrator] new_item from LLM: {new_item}")
                # Ensure we have a dict, handle both dict and None
                intent["new_item_data"] = new_item if new_item else {}
                logger.info(f"[Orchestrator] new_item_data: {intent['new_item_data']}")

            elif operation in ["remove_item", "remove_block", "remove_tool"]:
                logger.info(f"[Orchestrator] REMOVE operation detected, target from parsed: {parsed.get('target')}")
                intent["target"] = parsed.get("target")
                intent["target_index"] = parsed.get("target_index")
                intent["target_type"] = parsed.get("target_type")

            else:
                logger.warning(f"[Orchestrator] Unhandled operation: '{operation}'")

            logger.info(f"[Orchestrator] Final intent: {intent}")
            return intent

        except Exception as e:
            # Fallback to simple heuristics
            logger.error(f"[Orchestrator] LLM modification parsing failed: {e}", exc_info=True)
            prompt_lower = prompt.lower()

            # Check for delete/remove operations
            if "delete" in prompt_lower or "remove" in prompt_lower:
                # Try to determine what type to remove
                if "block" in prompt_lower:
                    return {
                        "operation": "remove_block",
                        "target": prompt,
                        "target_type": "blocks"
                    }
                elif "tool" in prompt_lower:
                    return {
                        "operation": "remove_tool",
                        "target": prompt,
                        "target_type": "tools"
                    }
                else:
                    # Default to item
                    return {
                        "operation": "remove_item",
                        "target": prompt,
                        "target_type": "items"
                    }
            elif "rare" in prompt_lower or "epic" in prompt_lower:
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


class SingleOperation(BaseModel):
    """A single operation within a batch modification request"""
    operation: str = Field(..., description="modify_property, add_item, add_block, add_tool, remove_item, remove_block, remove_tool")
    target: Optional[str] = Field(None, description="What to modify/remove (e.g., 'first item', 'ruby sword')")
    target_index: Optional[int] = Field(None, description="Index of item/block/tool (0-based)")
    target_type: Optional[str] = Field(None, description="items, blocks, or tools")
    property_name: Optional[str] = Field(None, description="Property to modify")
    property_value: Optional[Any] = Field(None, description="New value for the property")
    new_item: Optional[ParsedItem] = Field(None, description="New item/block/tool to add")


class ItemIntentParse(BaseModel):
    """Parsed intent from user prompt - supports multiple items"""
    items: List[ParsedItem] = Field(..., description="List of items/blocks/tools to create")
    inferred_mod_name: str = Field(..., description="Suggested mod name")


class ModificationIntentParse(BaseModel):
    """Parsed modification intent for existing spec - supports MULTIPLE operations"""
    operations: List[SingleOperation] = Field(
        default_factory=list,
        description="List of operations for batch requests (e.g., 'add X and Y', 'delete A and B')"
    )
    # Keep existing fields for backward compatibility / single operation
    operation: str = Field(..., description="modify_property, add_item, add_block, add_tool, remove_item, remove_block, remove_tool")
    target: Optional[str] = Field(None, description="What to modify (e.g., 'first item', 'ruby sword', 'all blocks')")
    target_index: Optional[int] = Field(None, description="Index of item/block/tool to modify (0-based)")
    target_type: Optional[str] = Field(None, description="items, blocks, or tools")
    property_name: Optional[str] = Field(None, description="Property to modify (e.g., 'rarity', 'luminance', 'hardness')")
    property_value: Optional[Any] = Field(None, description="New value for the property")
    new_item: Optional[ParsedItem] = Field(None, description="New item/block/tool to add (for add operations)")
    reasoning: str = Field(..., description="Why this interpretation was chosen")


__all__ = ["Orchestrator", "OrchestratorResponse", "ConversationContext"]
