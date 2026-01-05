# Agent Restructure Plan

## Current → New Architecture Mapping

### Current Structure
```
backend/agents/
├── langchain_agents.py       # LangChainModOrchestrator, ItemAgent, BlockAgent, PackagingAgent
├── mod_analyzer.py           # Simple wrapper
├── mod_generator.py          # File generation + compilation
├── image_generator.py        # Texture generation
└── reference_selector.py     # AI-powered texture selection
```

### New Structure (Based on WORKFLOW_DESIGN.md)
```
backend/agents/
├── core/
│   ├── __init__.py
│   ├── orchestrator.py       # 1. Conversation → Spec Delta
│   ├── spec_manager.py       # 2. Maintains canonical mod_spec.json
│   ├── compiler.py           # 3. Spec → IR (Intermediate Representation)
│   ├── planner.py            # 4. IR → Task DAG
│   ├── executor.py           # 5. Executes generation tasks
│   ├── validator.py          # 6. Pre-build validation
│   ├── builder.py            # 7. Gradle compilation
│   └── error_fixer.py        # 8. Error interpretation & deterministic fixing
├── tools/
│   ├── __init__.py
│   ├── image_generator.py    # KEEP: Texture generation
│   ├── reference_selector.py # KEEP: Reference texture selection
│   ├── code_generator.py     # NEW: Generates Java code from IR
│   ├── asset_generator.py    # NEW: Generates JSON/assets from IR
│   └── tool_registry.py      # NEW: Tool capability registry
├── schemas/
│   ├── __init__.py
│   ├── spec_schema.py        # JSON schema for mod_spec
│   ├── ir_schema.py          # JSON schema for mod_ir
│   └── task_schema.py        # JSON schema for task_dag
└── __init__.py
```

## Migration Strategy

### Phase 1: Create Core Pipeline (Priority)
1. **Orchestrator** - Extract conversational logic from langchain_agents.py
2. **Spec Manager** - Simple JSON persistence with versioning
3. **Compiler** - Convert spec to fully-specified IR
4. **Planner** - Build task dependency graph
5. **Executor** - Execute tasks using tools
6. **Validator** - Pre-build checks
7. **Builder** - Wrap existing Gradle logic from mod_generator.py
8. **Error Fixer** - Parse errors and generate patches

### Phase 2: Refactor Tools
1. Move `image_generator.py` → `tools/image_generator.py`
2. Move `reference_selector.py` → `tools/reference_selector.py`
3. Extract code generation from `mod_generator.py` → `tools/code_generator.py`
4. Extract asset generation from `mod_generator.py` → `tools/asset_generator.py`
5. Create `tool_registry.py` to declare tool capabilities

### Phase 3: Define Schemas
1. Create `spec_schema.py` - User intent format
2. Create `ir_schema.py` - Complete, deterministic blueprint
3. Create `task_schema.py` - Execution plan format

### Phase 4: Update Exports
1. Update `backend/agents/__init__.py`
2. Update API endpoints to use new pipeline
3. Remove old files after migration

## Key Principles (from WORKFLOW_DESIGN.md)

1. **Spec is for humans. IR is for machines.**
2. **No code generation without IR.**
3. **Generators must be dumb and deterministic.**
4. **All reasoning happens before execution.**
5. **Errors trigger patches, not retries.**

## What to Keep

### From `image_generator.py` ✅
- Entire ImageGenerator class
- Pixel art generation logic
- Minecraft palette quantization
- Background removal & edge cleanup

### From `reference_selector.py` ✅
- ReferenceSelector agent
- Texture catalog integration
- AI-powered similarity matching

### From `langchain_agents.py` ⚙️
- Prompt engineering for item/block design
- Pydantic models (ItemSpec, BlockSpec, etc.)
- Conversation patterns
→ **Move to Orchestrator**

### From `mod_generator.py` ⚙️
- Directory structure creation
- File templates
- Gradle compilation
→ **Split into Builder + Code/Asset Generator Tools**

## What to Remove

- `mod_analyzer.py` - Just a thin wrapper, merge into pipeline
- Old `langchain_agents.py` structure - Refactor into Orchestrator
- Direct LLM → Code generation - Must go through IR

## Next Steps

1. Create directory structure
2. Implement schemas first (defines contracts)
3. Implement core pipeline components
4. Move/refactor tools
5. Test end-to-end
6. Clean up old files
7. Update documentation
