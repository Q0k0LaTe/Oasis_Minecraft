# Archived Legacy Components

This directory contains legacy code from before the pipeline restructure.

## Files Archived

### langchain_agents.py (Legacy V1)
**Original purpose**: LangChain-based agents for mod generation
**Replaced by**: `core/orchestrator.py`, `core/compiler.py`, and the new pipeline architecture
**Date archived**: January 7, 2026

Contains:
- `LangChainModOrchestrator` - Legacy conversation handler
- `InteractiveItemAgent` - Item specification agent
- `BlockCreationAgent` - Block specification agent
- `PackagingAgent` - Packaging and compatibility agent

**Why archived**:
- Direct LLM → Code generation bypassed IR (Intermediate Representation)
- Not deterministic or debuggable
- Mixed concerns (reasoning + generation in same component)

### mod_analyzer.py (Legacy V1)
**Original purpose**: Simple wrapper around langchain_agents
**Replaced by**: `core/orchestrator.py` with `SpecManager`
**Date archived**: January 7, 2026

Contains:
- `ModAnalyzerAgent` - Thin wrapper for prompt analysis

**Why archived**:
- Just a wrapper, functionality now in Orchestrator
- Not needed in new architecture

### mod_generator.py (Partially Legacy)
**Original purpose**: Monolithic mod generator (60KB+)
**Replaced by**: Distributed tools in `tools/` directory
**Date archived**: January 7, 2026 (kept for V1 API compatibility)

Contains:
- Complete mod structure generation
- Java code generation
- Asset generation
- Gradle compilation
- All-in-one generation logic

**Why archived**:
- Monolithic design made it hard to test/maintain
- Mixed concerns (setup + generation + building)
- Tools extracted to: `workspace_tool.py`, `gradle_tool.py`, `java_code_tool.py`, `asset_tool.py`, `build_tool.py`

**Note**: This file is NOT fully archived yet - it's still used by V1 API (`/api/generate-mod`). Will be fully archived after V1 API is migrated to V2.

## New Architecture (V2)

The new architecture follows compiler design patterns:

```
User Prompt → Orchestrator → SpecManager → Compiler → Planner → Executor → Validator → Builder → JAR
```

### Key Improvements

1. **Separation of Concerns**
   - Orchestrator: Reasoning (LLM interactions)
   - Compiler: Transformation (Spec → IR)
   - Executor: Generation (mechanical execution)

2. **Determinism**
   - Same Spec always produces same IR
   - Same IR always produces same code
   - Tools are dumb and predictable

3. **Debuggability**
   - Clear pipeline stages
   - Execution logs
   - Spec versioning
   - Task DAG visualization

4. **Testability**
   - Each component can be tested in isolation
   - Mock-friendly interfaces
   - Reproducible failures

5. **Maintainability**
   - Small, focused components
   - Clear contracts (schemas)
   - Easy to add new tools

## Migration Path

### For V1 API Users
Continue using `/api/generate-mod` - no changes needed.

### For New Features
Use V2 API: `/api/v2/generate` with the new pipeline.

### Timeline
- V1 API: Maintained for backward compatibility
- V2 API: All new features implemented here
- Future: V1 will be deprecated once all features are migrated

## References

- [WORKFLOW_DESIGN.md](../../../../WORKFLOW_DESIGN.md) - Architecture design document
- [AGENT_RESTRUCTURE_PLAN.md](../../../../AGENT_RESTRUCTURE_PLAN.md) - Migration plan
- [AGENT_RESTRUCTURE_STATUS.md](../../../../AGENT_RESTRUCTURE_STATUS.md) - Implementation status
