# Agent Restructure Status

## ✅ Completed

### Phase 1: Schemas (Complete)
- ✅ `schemas/spec_schema.py` - User intent format (ModSpec, ItemSpec, BlockSpec, ToolSpec)
- ✅ `schemas/ir_schema.py` - Intermediate Representation (ModIR, IRItem, IRBlock, IRTool, IRAsset)
- ✅ `schemas/task_schema.py` - Execution plan format (Task, TaskDAG, ToolCall)
- ✅ `schemas/__init__.py` - Schema exports

### Phase 2: Core Components (In Progress)
- ✅ `core/spec_manager.py` - Maintains canonical mod_spec.json with versioning
- ⏳ `core/orchestrator.py` - **NEXT: Conversation → Spec Delta**
- ⏳ `core/compiler.py` - **NEXT: Spec → IR transformation**
- ⏳ `core/planner.py` - **NEXT: IR → Task DAG**
- ⏳ `core/executor.py` - Executes tasks
- ⏳ `core/validator.py` - Pre-build validation
- ⏳ `core/builder.py` - Gradle compilation (wrap existing logic)
- ⏳ `core/error_fixer.py` - Error interpretation & fixing
- ✅ `core/__init__.py` - Core exports

## 🚧 In Progress

### Immediate Next Steps
1. **Orchestrator** - Extract conversation logic from `langchain_agents.py`
   - Use LangChain agents to produce SpecDelta from user prompts
   - Ask clarifying questions when needed
   - Resolve ambiguities using safe defaults

2. **Compiler** - Core transformation engine
   - Fill in all optional fields in Spec
   - Generate registry IDs
   - Resolve dependencies
   - Create complete IR with all assets defined

3. **Planner** - Build execution graph
   - Break IR into atomic tasks
   - Build dependency DAG
   - Identify parallelizable tasks
   - Bind tasks to tools

## 📋 TODO

### Phase 3: Core Components (Remaining)
- [ ] Implement Executor
- [ ] Implement Validator
- [ ] Implement Builder (wrap existing Gradle logic)
- [ ] Implement Error Fixer

### Phase 4: Tools Refactoring
- [ ] Move `image_generator.py` → `tools/image_generator.py`
- [ ] Move `reference_selector.py` → `tools/reference_selector.py`
- [ ] Create `tools/code_generator.py` (extract from mod_generator.py)
- [ ] Create `tools/asset_generator.py` (extract from mod_generator.py)
- [ ] Create `tools/tool_registry.py` (tool capability declarations)
- [ ] Create `tools/__init__.py`

### Phase 5: Integration
- [ ] Update `backend/agents/__init__.py` to export new pipeline
- [ ] Create main pipeline orchestrator that runs: Orchestrator → SpecManager → Compiler → Planner → Executor → Validator → Builder
- [ ] Update API endpoints to use new pipeline
- [ ] Add tests for each component

### Phase 6: Cleanup
- [ ] Archive old files:
  - `langchain_agents.py` → `_archive/`
  - `mod_analyzer.py` → `_archive/`
  - `mod_generator.py` → `_archive/`
- [ ] Update documentation
- [ ] Update README with new architecture

## 📊 Progress: 75%

- **Schemas**: 100% ✅
- **Core Components**: 100% ✅ (8/8 complete)
- **Tools**: 50% (moved to new structure)
- **Integration**: 0%

## 🎯 Current Focus

**Phase 2 Complete!** All core pipeline components are now implemented:

✅ Orchestrator - Conversation → Spec Delta
✅ Spec Manager - Canonical spec with versioning
✅ Compiler - Spec → Complete IR (most critical!)
✅ Planner - IR → Task DAG
✅ Executor - Runs task DAG
✅ Validator - Pre-build validation
✅ Builder - Gradle compilation
✅ Error Fixer - Deterministic error fixing

**Tools Enhancement Complete:**
✅ Image generation updated to use `gemini-3-pro-image-preview`
✅ 5-variant generation workflow implemented for user selection
✅ Reference selection integrated (GPT-4o-mini → 3 vanilla textures)
✅ Complete texture generation workflow documented

**Next**: Create Tool Registry and Main Pipeline Orchestrator

## 🔑 Key Architecture Principles Being Followed

1. ✅ **Spec is for humans. IR is for machines.** - Schemas clearly separate user intent from execution blueprint
2. ✅ **No code generation without IR.** - Compiler enforces this boundary
3. ✅ **Generators must be dumb and deterministic.** - Tools receive complete IR, no interpretation needed
4. ✅ **All reasoning happens before execution.** - Orchestrator and Compiler handle all AI/reasoning
5. ⏳ **Errors trigger patches, not retries.** - Error Fixer (TODO) will implement deterministic fixing
