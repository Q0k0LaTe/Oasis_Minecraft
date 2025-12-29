# Agent Workflow Design - Structured JSON Decision Pipeline

## Overview

This document explains the **revised agent workflow** that uses pure **JSON-based decisions** instead of text parsing. Every decision is made through structured Pydantic models with explicit validation.

## Problem with Previous Approach

The old system had **mixed approaches**:

1. **Legacy Gemini Fallback** - Used string parsing and regex
2. **LangChain Pipeline** - Used Pydantic models but lacked clear separation

This led to:
- Inconsistent naming logic scattered across multiple files
- Difficult to debug which agent decided what
- No single source of truth for naming conventions

## New Architecture

### Multi-Stage Decision Pipeline

```
User Prompt
     │
     ▼
┌─────────────────────────┐
│  Stage 1: Naming Agent  │  ◄─── Decides mod_name, mod_id, item_name, item_id
│  Output: NamingDecision │       Single source of truth for all identifiers
└────────────┬────────────┘
             │
             ▼
┌──────────────────────────────┐
│  Stage 2: Properties Agent   │  ◄─── Decides rarity, stack size, creative tab
│  Output: PropertiesDecision  │       Game balance and mechanics
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│  Stage 3: Block Agent        │  ◄─── (Optional) Companion block
│  Output: BlockDecision       │       Uses naming + properties from previous stages
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│  Stage 4: Tool Agent         │  ◄─── (Optional) Companion tool
│  Output: ToolDecision        │       Uses all previous decisions
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│  Final: Unified Decision     │  ◄─── Combines all stages
│  Output: UnifiedModDecision  │       Single JSON output for generator
└──────────────────────────────┘
```

## Stage 1: Naming Agent

### Purpose
Single source of truth for **all naming decisions**.

### JSON Output Schema

```json
{
  "mod_name": "Ruby Gems Mod",
  "mod_id": "rubygemsmod",
  "item_name": "Ruby Gem",
  "item_id": "ruby_gem",
  "namespace": "minecraft",
  "naming_rationale": "Based on 'ruby gem' in user prompt..."
}
```

### Validation Rules

- `mod_id`: Must match pattern `^[a-z0-9]+$` (no underscores, no spaces)
- `item_id`: Must match pattern `^[a-z0-9_]+$` (underscores allowed)
- Both are automatically validated by Pydantic
- Both are normalized and cleaned during validation

### Override Support

If user provides `mod_name_override`, the agent:
1. Uses the override as `mod_name`
2. Automatically generates valid `mod_id` from it
3. Documents this in `naming_rationale`

## Stage 2: Properties Agent

### Purpose
Decide **gameplay properties** and **game balance**.

### JSON Output Schema

```json
{
  "max_stack_size": 16,
  "rarity": "RARE",
  "fireproof": false,
  "creative_tab": "INGREDIENTS",
  "special_ability": "Grants fire resistance when held",
  "gameplay_tags": ["valuable", "magical"],
  "balance_reasoning": "RARE rarity because magical properties..."
}
```

### Validation Rules

- `max_stack_size`: Integer between 1-64
- `rarity`: Must be one of: COMMON, UNCOMMON, RARE, EPIC
- `creative_tab`: Must be valid Minecraft creative tab
- All validated by Pydantic at runtime

### Decision Logic

The agent considers:
1. Item type (weapon, tool, material, food, etc.)
2. User-described power level
3. Minecraft balance conventions
4. Rarity → stack size correlation

## Benefits of This Approach

### 1. No Text Parsing

**Old way:**
```python
# Fragile regex parsing
item_name = extract_name_from_text(ai_response)
mod_id = item_name.lower().replace(" ", "")
```

**New way:**
```python
# Structured JSON enforced by Pydantic
naming = naming_agent.decide(user_prompt)
# naming.mod_id is guaranteed valid
```

### 2. Clear Separation of Concerns

Each agent has **ONE** responsibility:
- `NamingAgent` → Names and IDs only
- `PropertiesAgent` → Gameplay properties only
- `BlockAgent` → Block specifications only
- `ToolAgent` → Tool specifications only

### 3. Explicit Validation

Pydantic models validate:
- Required fields are present
- Types are correct (int, str, bool, etc.)
- Values match constraints (regex patterns, min/max)
- Nested structures are valid

### 4. Easy to Debug

```python
decision = orchestrator.run_decision_pipeline(prompt)

# Every stage logged:
# [Stage 1: Naming] mod='Ruby Mod' (rubymod), item='Ruby Gem' (ruby_gem)
# [Stage 2: Properties] RARE rarity, stack=16, tab=INGREDIENTS
```

### 5. Backward Compatible

```python
# New structured format
decision = orchestrator.run_decision_pipeline(prompt)

# Convert to legacy format for existing code
legacy_dict = decision.to_legacy_format()
# Works with existing ModGenerator without changes
```

## Integration with Existing System

### Option A: Direct Replacement

Replace the current analyzer in `main.py`:

```python
# Old
from agents.mod_analyzer import ModAnalyzerAgent
analyzer = ModAnalyzerAgent()

# New
from agents.decision_workflow import DecisionOrchestrator
orchestrator = DecisionOrchestrator()

# Usage
decision = orchestrator.run_decision_pipeline(
    user_prompt=prompt,
    author_name=author_name,
    mod_name_override=mod_name
)
ai_spec = decision.to_legacy_format()
```

### Option B: Gradual Migration

Keep both systems running:

```python
from agents.mod_analyzer import ModAnalyzerAgent
from agents.decision_workflow import DecisionOrchestrator

# Try new workflow, fallback to old
try:
    orchestrator = DecisionOrchestrator()
    decision = orchestrator.run_decision_pipeline(prompt)
    ai_spec = decision.to_legacy_format()
except Exception as e:
    print(f"New workflow failed, using legacy: {e}")
    analyzer = ModAnalyzerAgent()
    ai_spec = analyzer.analyze(prompt)
```

## How Mod Name is Decided

### Current Flow

1. User enters prompt: `"Create a powerful ruby gem"`
2. `NamingAgent` receives prompt
3. AI analyzes the prompt using **structured JSON output parser**
4. AI generates:
   ```json
   {
     "mod_name": "Ruby Gem Mod",
     "mod_id": "rubygemmod",
     "item_name": "Ruby Gem",
     "item_id": "ruby_gem",
     "naming_rationale": "Based on 'ruby gem' mentioned in prompt, created a focused gem-themed mod"
   }
   ```
5. Pydantic validates the output
6. If user provided `mod_name_override`, it replaces `mod_name`
7. Output is **guaranteed** to be valid JSON

### No Parsing Required

The key insight: **LangChain's PydanticOutputParser forces the AI to output valid JSON**. We're not parsing text - we're using Pydantic schemas as contracts that the AI must follow.

## Testing the New Workflow

```bash
cd backend
python agents/decision_workflow.py
```

Example output:
```
[DecisionPipeline] Stage 1: Naming decisions...
[DecisionPipeline] ✓ Naming: mod='Ruby Gems Mod' (rubygemsmod), item='Ruby Gem' (ruby_gem)
[DecisionPipeline] Stage 2: Properties & balance...
[DecisionPipeline] ✓ Properties: RARE rarity, stack=16, tab=INGREDIENTS
[DecisionPipeline] ✓ Complete decision pipeline finished

Decision: {
  "naming": {
    "mod_name": "Ruby Gems Mod",
    "mod_id": "rubygemsmod",
    ...
  },
  "properties": {
    "max_stack_size": 16,
    "rarity": "RARE",
    ...
  }
}
```

## Future Enhancements

### 1. Add Conversation Memory

```python
class DecisionOrchestrator:
    def __init__(self):
        self.conversation_history = []

    def run_decision_pipeline(self, user_prompt):
        # Pass history to agents
        naming = self.naming_agent.decide(
            user_prompt,
            conversation_history=self.conversation_history
        )
        # Update history
        self.conversation_history.append({
            "role": "user",
            "content": user_prompt
        })
```

### 2. Add User Confirmation Step

```python
# After Stage 1
naming = naming_agent.decide(prompt)

# Ask user to confirm
if not confirm_with_user(naming):
    # Let user edit
    naming = user_edit_naming(naming)
```

### 3. Add Caching Layer

```python
@cache_decision(ttl=3600)
def run_decision_pipeline(prompt):
    # Expensive AI calls
    ...
```

## Conclusion

The new workflow:
- ✅ Uses **pure JSON** via Pydantic models
- ✅ **No text parsing** or regex hacking
- ✅ **Clear separation** of concerns
- ✅ **Explicit validation** at every stage
- ✅ **Easy to debug** with structured logging
- ✅ **Backward compatible** with legacy format
- ✅ **Mod name** is decided by dedicated NamingAgent with explicit rules

This makes the system more maintainable, testable, and reliable.
