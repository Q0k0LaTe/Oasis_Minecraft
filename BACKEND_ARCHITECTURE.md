# Backend Architecture - Complete Guide

## Table of Contents
1. [High-Level Overview](#high-level-overview)
2. [Directory Structure](#directory-structure)
3. [Core Components](#core-components)
4. [Agent Architecture](#agent-architecture)
5. [Request Flow](#request-flow)
6. [Detailed File Breakdown](#detailed-file-breakdown)
7. [How Everything Connects](#how-everything-connects)

---

## High-Level Overview

The backend is a **FastAPI-based microservice** that orchestrates AI agents to generate Minecraft mods from natural language descriptions. It uses:

- **Google Gemini** as the LLM (Large Language Model)
- **LangChain** for multi-agent orchestration
- **Pydantic** for data validation and structured outputs
- **Background tasks** for async job processing
- **In-memory job storage** (in production, use Redis/database)

### Architecture Pattern

```
Frontend Request
      ↓
FastAPI Endpoints (main.py)
      ↓
Background Task (async processing)
      ↓
Multi-Agent Pipeline
      ↓
┌─────────────────────────────────────┐
│   Agent Orchestration Layers        │
├─────────────────────────────────────┤
│ 1. ModAnalyzerAgent (entry point)   │
│    ├─→ LangChainModOrchestrator     │
│    │   ├─→ InteractiveItemAgent     │
│    │   ├─→ BlockCreationAgent       │
│    │   ├─→ ToolCreationAgent        │
│    │   └─→ PackagingAgent           │
│    └─→ Legacy Gemini Fallback       │
│                                      │
│ 2. ImageGenerator                   │
│    └─→ Generates 5 texture options  │
│                                      │
│ 3. ModGenerator                     │
│    └─→ Creates Java/Gradle files    │
└─────────────────────────────────────┘
      ↓
Job Storage (in-memory dict)
      ↓
Frontend Polling (status updates)
```

---

## Directory Structure

```
backend/
├── agents/                      # AI agent system
│   ├── __init__.py             # Package initialization
│   ├── decision_workflow.py    # NEW: Structured JSON pipeline
│   ├── langchain_agents.py     # Multi-agent orchestration (CURRENT)
│   ├── mod_analyzer.py         # Entry point + fallback
│   ├── image_generator.py      # Texture generation
│   └── mod_generator.py        # Code generation
│
├── templates/                   # Gradle/Fabric templates
│   └── gradle_wrapper_template/
│
├── generated/                   # Temp mod projects (gitignored)
├── downloads/                   # Built .jar files (gitignored)
│
├── config.py                    # Configuration
├── main.py                      # FastAPI application
├── models.py                    # Pydantic schemas
└── requirements.txt             # Python dependencies
```

---

## Core Components

### 1. FastAPI Application (`main.py`)

**Purpose**: HTTP server that exposes REST API endpoints

**Key Responsibilities**:
- Accept user prompts via POST requests
- Queue background jobs for async processing
- Poll job status and return results
- Handle image selection workflow
- Serve downloadable .jar files

**Main Endpoints**:
```python
POST   /api/generate-mod              # Start new mod generation
GET    /api/status/{job_id}           # Get job status/logs
POST   /api/jobs/{job_id}/select-image      # User selects texture
POST   /api/jobs/{job_id}/regenerate-images # Generate new textures
GET    /downloads/{filename}          # Download .jar file
```

### 2. Configuration (`config.py`)

**Purpose**: Centralized configuration management

**What it contains**:
```python
# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# AI Models
AI_MODEL = "gemini-1.5-flash"
AI_TEMPERATURE = 0.7

# Minecraft Versions
MINECRAFT_VERSION = "1.21.5"
FABRIC_LOADER_VERSION = "0.16.13"
FABRIC_API_VERSION = "0.128.2+1.21.5"

# Server
HOST = "127.0.0.1"
PORT = 3000

# Paths
DOWNLOADS_DIR = Path(__file__).parent / "downloads"
GENERATED_DIR = Path(__file__).parent / "generated"
```

### 3. Data Models (`models.py`)

**Purpose**: Define data structures with validation using Pydantic

**Key Models**:

```python
ItemPromptRequest       # Incoming user request
WorklistEntry          # Single worklist item
ItemProperties         # Item gameplay properties
BlockProperties        # Block specifications
ToolProperties         # Tool statistics
AIDecisions           # Complete AI analysis output
GenerateModResponse   # Final response to frontend
```

**Example**:
```python
class ItemPromptRequest(BaseModel):
    prompt: Optional[str] = None
    authorName: Optional[str] = None
    modName: Optional[str] = None
    worklist: Optional[List[WorklistEntry]] = None
```

---

## Agent Architecture

This is the **heart of the system**. There are THREE agent systems:

### System 1: NEW - Structured Decision Workflow (`decision_workflow.py`)

**Status**: Newly created, not yet integrated into main.py

**Purpose**: Clean, multi-stage JSON-based decision pipeline

**Architecture**:

```python
DecisionOrchestrator
    │
    ├─→ Stage 1: NamingAgent
    │   Input: user_prompt, mod_name_override
    │   Output: NamingDecision (JSON)
    │   ├─ mod_name: "Ruby Gems Mod"
    │   ├─ mod_id: "rubygemsmod"
    │   ├─ item_name: "Ruby Gem"
    │   └─ item_id: "ruby_gem"
    │
    ├─→ Stage 2: PropertiesAgent
    │   Input: user_prompt, NamingDecision
    │   Output: PropertiesDecision (JSON)
    │   ├─ max_stack_size: 16
    │   ├─ rarity: "RARE"
    │   ├─ fireproof: false
    │   └─ creative_tab: "INGREDIENTS"
    │
    └─→ Final: UnifiedModDecision
        Combines all stages into one object
        Can convert to legacy format
```

**Key Classes**:

1. **NamingAgent**: Decides all names and IDs
   - Uses `PydanticOutputParser` to force structured JSON
   - Validates IDs match Minecraft conventions
   - Supports mod name override

2. **PropertiesAgent**: Decides gameplay properties
   - Considers item type (weapon, tool, material)
   - Balances rarity with stack size
   - Assigns appropriate creative tab

3. **DecisionOrchestrator**: Runs the pipeline
   - Calls agents in sequence
   - Each stage builds on previous
   - Returns `UnifiedModDecision`

**Example Usage**:
```python
orchestrator = DecisionOrchestrator()
decision = orchestrator.run_decision_pipeline(
    user_prompt="Create a powerful ruby gem",
    author_name="Steve",
    mod_name_override="My Ruby Mod"
)

# Structured output
print(decision.naming.mod_name)     # "My Ruby Mod"
print(decision.naming.mod_id)       # "myrubymod"
print(decision.properties.rarity)   # "RARE"

# Convert to legacy format for compatibility
legacy = decision.to_legacy_format()
```

---

### System 2: CURRENT - LangChain Multi-Agent (`langchain_agents.py`)

**Status**: Currently active in production

**Purpose**: Full-featured multi-agent system with blocks, tools, and packaging

**Architecture**:

```python
LangChainModOrchestrator
    │
    ├─→ 1. InteractiveItemAgent
    │   ├─ Input: user_prompt, conversation_history, mod_name_override
    │   ├─ Output: ItemSpec (Pydantic model)
    │   ├─ Decides: mod_name, mod_id, item_name, item_id, properties
    │   └─ Features: conversation context, clarifying questions
    │
    ├─→ 2. BlockCreationAgent
    │   ├─ Input: user_prompt, ItemSpec
    │   ├─ Output: BlockSpec (Pydantic model)
    │   ├─ Decides: block_name, properties (hardness, luminance, etc.)
    │   └─ Creates companion storage block for the item
    │
    ├─→ 3. Tool Derivation (deterministic, not AI)
    │   ├─ Input: ItemSpec, BlockSpec
    │   ├─ Output: ToolSpec (crafted from rarity)
    │   ├─ Decides: tool_type (pickaxe, sword, axe), stats
    │   └─ Generates crafting recipes
    │
    ├─→ 4. PackagingAgent
    │   ├─ Input: ItemSpec, BlockSpec
    │   ├─ Output: PackagingPlan (Pydantic model)
    │   └─ Decides: build steps, asset plan, QA notes
    │
    └─→ Final: Combined Payload (dict)
        Backwards-compatible with old format
```

**Key Classes**:

1. **InteractiveItemAgent**
   ```python
   class InteractiveItemAgent:
       def __init__(self, llm):
           self.llm = llm
           self.parser = PydanticOutputParser(pydantic_object=ItemSpec)
           self.prompt = ChatPromptTemplate(...)

       def run(self, user_prompt, conversation_history, mod_name_override):
           # AI generates ItemSpec in JSON format
           # Pydantic validates and parses
           return ItemSpec(...)
   ```

2. **BlockCreationAgent**
   ```python
   class BlockCreationAgent:
       def run(self, user_prompt, item_spec):
           # AI designs a companion block
           # Considers item rarity and theme
           return BlockSpec(
               block_name="Ruby Block",
               properties=BlockPropertiesSpec(
                   material="METAL",
                   hardness=5.0,
                   resistance=6.0,
                   luminance=8,
                   requires_tool=True
               )
           )
   ```

3. **Tool Derivation** (not AI, uses logic)
   ```python
   def _derive_tool_spec(self, user_prompt, item_spec, block_spec):
       # Deterministic based on rarity
       rarity = item_spec.properties.rarity

       tier_settings = {
           "COMMON": {"material": "IRON", "durability": 375, ...},
           "RARE": {"material": "DIAMOND", "durability": 1561, ...},
           "EPIC": {"material": "NETHERITE", "durability": 2031, ...}
       }

       # Infer tool type from prompt
       tool_type = self._infer_tool_type(user_prompt, item_spec)

       return ToolSpec(...)
   ```

4. **LangChainModOrchestrator**
   ```python
   def run_pipeline(self, user_prompt, author_name, mod_name_override):
       # Stage 1
       item_spec = self.item_agent.run(user_prompt, ...)

       # Stage 2
       block_spec = self.block_agent.run(user_prompt, item_spec)

       # Stage 3 (deterministic)
       tool_spec = self._derive_tool_spec(user_prompt, item_spec, block_spec)

       # Stage 4
       packaging = self.packaging_agent.run(user_prompt, item_spec, block_spec)

       # Combine into dict
       return self._compose_payload(item_spec, block_spec, tool_spec, packaging)
   ```

**Output Format** (backwards compatible):
```python
{
    "modName": "Ruby Gems Mod",
    "modId": "rubygemsmod",
    "itemName": "Ruby Gem",
    "itemId": "ruby_gem",
    "description": "A powerful ruby gem...",
    "author": "Steve",
    "properties": {
        "maxStackSize": 16,
        "rarity": "RARE",
        "fireproof": False,
        "creativeTab": "INGREDIENTS",
        "specialAbility": "Grants fire resistance"
    },
    "block": {
        "blockName": "Ruby Block",
        "blockId": "ruby_block",
        "properties": {...},
        "variants": [...]
    },
    "tool": {
        "toolName": "Ruby Pickaxe",
        "toolId": "ruby_pickaxe",
        "properties": {...},
        "forgingRecipe": {...}
    },
    "packagingPlan": {
        "build_steps": [...],
        "asset_plan": [...],
        "qa_notes": [...]
    }
}
```

---

### System 3: LEGACY - Gemini Fallback (`mod_analyzer.py`)

**Status**: Fallback when LangChain fails

**Purpose**: Simple, reliable analyzer using direct Gemini API calls

**Architecture**:

```python
ModAnalyzerAgent
    │
    ├─→ Try: LangChainModOrchestrator (System 2)
    │   └─ Returns structured dict
    │
    └─→ Fallback: _legacy_openai_analyze()
        ├─ Direct Gemini API call
        ├─ AI returns JSON string
        ├─ Parse with json.loads()
        └─ Returns simple dict
```

**Code Flow**:
```python
class ModAnalyzerAgent:
    def analyze(self, user_prompt, author_name, mod_name_override):
        try:
            # Try LangChain multi-agent
            return self.orchestrator.run_pipeline(
                user_prompt, author_name, mod_name_override
            )
        except Exception as e:
            # Fallback to simple Gemini
            return self._legacy_openai_analyze(
                user_prompt, author_name, mod_name_override
            )

    def _legacy_openai_analyze(self, user_prompt, ...):
        # Direct Gemini call
        response_text = self._call_gemini(user_prompt)

        # Parse JSON
        spec_data = json.loads(response_text)

        # Simple dict
        return {
            "modName": spec_data['mod_name'],
            "modId": spec_data['mod_id'],
            "itemName": spec_data['item_name'],
            ...
        }
```

**System Prompt** (for Gemini):
```
You are an expert Minecraft mod designer.
Decide:
1. Mod name and ID
2. Item name and ID
3. Max stack size (1/16/64)
4. Rarity (COMMON/UNCOMMON/RARE/EPIC)
5. Fireproof status
6. Creative tab

Respond ONLY with valid JSON:
{
  "mod_name": "string",
  "mod_id": "string",
  "item_name": "string",
  "item_id": "string",
  "max_stack_size": number,
  "rarity": "COMMON|UNCOMMON|RARE|EPIC",
  "fireproof": boolean,
  "creative_tab": "string",
  "special_ability": "string",
  "reasoning": "string"
}
```

---

## Image Generator (`image_generator.py`)

**Purpose**: Generate texture options using AI image generation

**Current Implementation**: Placeholder/simple generator
**Future**: Could use Gemini's imagen or DALL-E

**Architecture**:
```python
class ImageGenerator:
    def generate_multiple_item_textures(self, item_description, item_name, count=5):
        """Generate 5 texture options for user to choose"""
        textures = []
        for i in range(count):
            # Generate 16x16 pixel art texture
            texture = self._generate_single_texture(item_description)
            textures.append(texture)
        return textures

    def generate_multiple_block_textures(self, block_spec, count=5):
        """Generate 5 block texture options"""
        ...

    def generate_multiple_tool_textures(self, tool_spec, count=5):
        """Generate 5 tool texture options"""
        ...
```

**Output**: List of binary PNG data (16x16 pixel art)

---

## Mod Generator (`mod_generator.py`)

**Purpose**: Convert AI decisions into actual Minecraft mod code

**Architecture**:

```python
class ModGenerator:
    def generate_mod(self, ai_spec, job_id, progress_callback):
        """
        Generate complete Fabric mod from AI specification

        Steps:
        1. Create project directory
        2. Copy Gradle wrapper
        3. Generate Java files
        4. Generate JSON files
        5. Generate textures
        6. Compile with Gradle
        7. Return .jar file
        """

        # 1. Setup
        mod_dir = GENERATED_DIR / job_id / ai_spec['modId']

        # 2. Gradle
        self._copy_gradle_wrapper(mod_dir)
        self._generate_build_gradle(mod_dir, ai_spec)

        # 3. Java code
        self._generate_main_mod_class(mod_dir, ai_spec)
        self._generate_items_class(mod_dir, ai_spec)
        self._generate_blocks_class(mod_dir, ai_spec)  # if block exists

        # 4. Resources
        self._generate_fabric_mod_json(mod_dir, ai_spec)
        self._generate_lang_file(mod_dir, ai_spec)
        self._generate_item_models(mod_dir, ai_spec)
        self._generate_block_models(mod_dir, ai_spec)  # if block exists

        # 5. Textures
        self._save_textures(mod_dir, selected_textures)

        # 6. Compile
        jar_path = self._compile_mod(mod_dir)

        # 7. Return
        return {
            "success": True,
            "downloadUrl": f"/downloads/{jar_path.name}"
        }
```

**Example Generated Files**:

1. **Main Mod Class** (`GenerateamodmodMod.java`):
```java
package com.example.generateamodmod;

import net.fabricmc.api.ModInitializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class GenerateamodmodMod implements ModInitializer {
    public static final String MOD_ID = "generateamodmod";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    @Override
    public void onInitialize() {
        LOGGER.info("Initializing Generateamodmod Mod");
        ModItems.registerItems();
        ModBlocks.registerBlocks();
    }
}
```

2. **Items Registry** (`ModItems.java`):
```java
package com.example.generateamodmod.item;

import net.minecraft.item.Item;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.util.Identifier;

public class ModItems {
    public static final Item GENERATE_A_MOD = registerItem("generate_a_mod",
        new Item(new Item.Settings().maxCount(16).fireproof()));

    private static Item registerItem(String name, Item item) {
        return Registry.register(Registries.ITEM,
            Identifier.of(GenerateamodmodMod.MOD_ID, name), item);
    }

    public static void registerItems() {
        GenerateamodmodMod.LOGGER.info("Registering items");
    }
}
```

3. **fabric.mod.json** (metadata):
```json
{
  "schemaVersion": 1,
  "id": "generateamodmod",
  "version": "1.0.0",
  "name": "Generateamodmod Mod",
  "description": "AI-generated mod",
  "authors": ["AI Generator"],
  "contact": {},
  "license": "MIT",
  "icon": "assets/generateamodmod/icon.png",
  "environment": "*",
  "entrypoints": {
    "main": ["com.example.generateamodmod.GenerateamodmodMod"]
  },
  "depends": {
    "fabricloader": ">=0.16.0",
    "minecraft": "1.21.5",
    "java": ">=21",
    "fabric-api": "*"
  }
}
```

4. **Item Model JSON** (`models/item/generate_a_mod.json`):
```json
{
  "parent": "item/generated",
  "textures": {
    "layer0": "generateamodmod:item/generate_a_mod"
  }
}
```

---

## Request Flow

### Complete Flow: From Frontend to .jar File

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. USER SUBMITS PROMPT                                               │
└─────────────────────────────────────────────────────────────────────┘
    Frontend: "Create a powerful ruby gem"
    POST /api/generate-mod
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 2. FASTAPI CREATES JOB (main.py)                                    │
└─────────────────────────────────────────────────────────────────────┘
    job_id = uuid.uuid4()  # "abc-123-def-456"
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "logs": ["Job queued..."],
        "spec": None,
        "result": None
    }

    background_tasks.add_task(run_generation_task, job_id, request_data)

    return {"jobId": "abc-123-def-456"}
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 3. FRONTEND STARTS POLLING                                          │
└─────────────────────────────────────────────────────────────────────┘
    Every 2 seconds:
    GET /api/status/abc-123-def-456

    Returns:
    {
        "status": "analyzing",
        "progress": 10,
        "logs": ["Analyzing prompt...", "AI deciding properties..."]
    }
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 4. BACKGROUND TASK STARTS (main.py::run_generation_task)           │
└─────────────────────────────────────────────────────────────────────┘
    jobs[job_id].update({"status": "analyzing", "progress": 10})
    append_job_log(job_id, "Analyzing prompt with AI agent...")
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 5. MOD ANALYZER AGENT (mod_analyzer.py)                            │
└─────────────────────────────────────────────────────────────────────┘
    analyzer = ModAnalyzerAgent()
    ai_spec = analyzer.analyze(
        user_prompt="Create a powerful ruby gem",
        author_name=None,
        mod_name_override=None
    )

    Internally:
    ├─→ Try: orchestrator.run_pipeline()  # LangChain multi-agent
    │   ├─→ InteractiveItemAgent: decides names & properties
    │   ├─→ BlockCreationAgent: creates companion block
    │   ├─→ Tool derivation: creates mining tool
    │   └─→ PackagingAgent: plans assembly
    │
    └─→ Fallback: _legacy_openai_analyze()  # Direct Gemini
        └─→ Returns simple JSON dict

    Returns:
    {
        "modName": "Ruby Gems Mod",
        "modId": "rubygemsmod",
        "itemName": "Ruby Gem",
        "itemId": "ruby_gem",
        "properties": {...},
        "block": {...},
        "tool": {...}
    }
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 6. IMAGE GENERATION (image_generator.py)                            │
└─────────────────────────────────────────────────────────────────────┘
    jobs[job_id].update({"status": "generating_images", "progress": 35})
    append_job_log(job_id, "Generating 5 texture options...")

    image_gen = ImageGenerator()

    # Generate item textures
    item_textures = image_gen.generate_multiple_item_textures(
        item_description=ai_spec['description'],
        item_name=ai_spec['itemName'],
        count=5
    )
    # Returns: [binary_png_1, binary_png_2, binary_png_3, binary_png_4, binary_png_5]

    # Encode to base64 for frontend
    pending_selections["item"] = {
        "name": "Ruby Gem",
        "options": [base64.b64encode(t).decode() for t in item_textures]
    }

    # If block exists, generate block textures too
    if ai_spec.get("block"):
        block_textures = image_gen.generate_multiple_block_textures(...)
        pending_selections["block"] = {...}

    # If tool exists, generate tool textures
    if ai_spec.get("tool"):
        tool_textures = image_gen.generate_multiple_tool_textures(...)
        pending_selections["tool"] = {...}
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 7. PAUSE FOR USER SELECTION                                         │
└─────────────────────────────────────────────────────────────────────┘
    jobs[job_id].update({
        "status": "awaiting_image_selection",
        "progress": 50,
        "pendingImageSelection": pending_selections
    })

    # Background task STOPS here
    # Waiting for user input...
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 8. FRONTEND SHOWS MODAL                                             │
└─────────────────────────────────────────────────────────────────────┘
    Frontend receives status "awaiting_image_selection"

    Opens modal showing:
    ┌───────────────────────────────────┐
    │ Choose Texture (1/3)              │
    │ Ruby Gem - ITEM                   │
    ├───────────────────────────────────┤
    │ [img1] [img2] [img3] [img4] [img5]│
    │                                   │
    │ [Regenerate 5 More]               │
    └───────────────────────────────────┘

    User clicks img3
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 9. USER SELECTS TEXTURE                                             │
└─────────────────────────────────────────────────────────────────────┘
    POST /api/jobs/abc-123-def-456/select-image
    Body: {
        "assetType": "item",
        "selectedIndex": 2
    }

    Backend stores selection:
    jobs[job_id]["selections"]["item"] = base64_image_data

    If all assets selected:
    jobs[job_id].update({"status": "generating"})
    background_tasks.add_task(continue_generation_after_selection, job_id)
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 10. CODE GENERATION (mod_generator.py)                              │
└─────────────────────────────────────────────────────────────────────┘
    jobs[job_id].update({"status": "generating", "progress": 60})
    append_job_log(job_id, "Generating Java code...")

    generator = ModGenerator()
    generation_result = generator.generate_mod_with_selected_images(
        ai_spec,
        job_id,
        selections={
            "item": base64_image_item,
            "block": base64_image_block,
            "tool": base64_image_tool
        },
        progress_callback=lambda msg: append_job_log(job_id, msg)
    )

    Internally:
    1. Create directory: backend/generated/abc-123-def-456/rubygemsmod/
    2. Copy Gradle wrapper
    3. Generate build.gradle
    4. Generate src/main/java/com/example/rubygemsmod/RubygemsmodMod.java
    5. Generate src/main/java/.../item/ModItems.java
    6. Generate src/main/java/.../block/ModBlocks.java
    7. Generate src/main/resources/fabric.mod.json
    8. Generate src/main/resources/assets/rubygemsmod/lang/en_us.json
    9. Generate src/main/resources/assets/rubygemsmod/models/item/*.json
    10. Decode base64 textures and save as .png files
    11. Run: ./gradlew build
    12. Move: build/libs/rubygemsmod-1.0.0.jar → backend/downloads/

    Returns:
    {
        "success": True,
        "downloadUrl": "/downloads/rubygemsmod-1.0.0.jar"
    }
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 11. JOB COMPLETE                                                     │
└─────────────────────────────────────────────────────────────────────┘
    jobs[job_id].update({
        "status": "completed",
        "progress": 100,
        "result": {
            "success": True,
            "jobId": "abc-123-def-456",
            "aiDecisions": ai_spec,
            "downloadUrl": "/downloads/rubygemsmod-1.0.0.jar",
            "textureBase64": selections["item"],
            "message": "Mod generated successfully!"
        }
    })
    append_job_log(job_id, "Job completed successfully.")
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 12. FRONTEND DISPLAYS RESULT                                        │
└─────────────────────────────────────────────────────────────────────┘
    Frontend polls and gets status="completed"

    Shows result card:
    ┌─────────────────────────────────┐
    │ [texture] Ruby Gem              │
    │ rubygemsmod:ruby_gem            │
    │ [RARE] [INGREDIENTS]            │
    ├─────────────────────────────────┤
    │ Code: // Ruby Gems Mod gen...   │
    ├─────────────────────────────────┤
    │ ⬇ Download rubygemsmod.jar      │
    └─────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 13. USER DOWNLOADS .JAR                                              │
└─────────────────────────────────────────────────────────────────────┘
    GET /downloads/rubygemsmod-1.0.0.jar

    Backend:
    return FileResponse(
        path=DOWNLOADS_DIR / "rubygemsmod-1.0.0.jar",
        filename="rubygemsmod-1.0.0.jar",
        media_type="application/java-archive"
    )

    User places in .minecraft/mods/ folder
    Launches Minecraft 1.21.5 with Fabric
    Ruby Gem appears in creative inventory!
```

---

## Detailed File Breakdown

### `main.py` - FastAPI Application

**Line-by-line breakdown**:

```python
# Lines 1-15: Imports
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from models import ItemPromptRequest
from agents.mod_analyzer import ModAnalyzerAgent
from agents.mod_generator import ModGenerator
from agents.image_generator import ImageGenerator

# Lines 16-30: App initialization
app = FastAPI(title="Minecraft Mod Generator API")
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# Lines 32-38: Initialize agents (singleton pattern)
analyzer = ModAnalyzerAgent()      # AI analyzer
generator = ModGenerator()         # Code generator

# Lines 36-37: In-memory job storage (simple dict)
jobs = {}  # {job_id: {status, progress, logs, spec, result}}

# Lines 40-49: Helper functions
def append_job_log(job_id, message):
    """Add log entry to job (keep last 150)"""
    job = jobs.get(job_id)
    logs = job.setdefault("logs", [])
    logs.append(message)
    if len(logs) > 150:
        job["logs"] = logs[-150:]

# Lines 51-332: Main generation task (background)
def run_generation_task(job_id, request_payload):
    """
    Background task that does all the work.

    Flow:
    1. Update job status to "analyzing"
    2. Call ModAnalyzerAgent to get AI decisions
    3. Update job status to "generating_images"
    4. Call ImageGenerator to create texture options
    5. Update job status to "awaiting_image_selection"
    6. PAUSE (wait for user input)
    7. (Later) Resume with continue_generation_after_selection()
    """

    # Line 174-177: Handle worklist vs single prompt
    worklist = request_payload.get("worklist") or []
    prompt = request_payload.get("prompt")

    # Lines 179-249: Batch processing (if worklist)
    if worklist:
        # Process each entry
        for entry in worklist:
            ai_spec = analyzer.analyze(entry["prompt"], ...)
            generation_result = generator.generate_mod(ai_spec, ...)
            batch_results.append(...)

    # Lines 251-320: Single prompt processing
    else:
        # Step 1: AI Analysis
        ai_spec = analyzer.analyze(prompt, ...)

        # Step 2: Generate textures
        image_gen = ImageGenerator()
        item_textures = image_gen.generate_multiple_item_textures(...)

        # Step 3: Pause for selection
        jobs[job_id].update({
            "status": "awaiting_image_selection",
            "pendingImageSelection": {
                "item": {"options": [base64_textures...]},
                "block": {...},
                "tool": {...}
            }
        })

# Lines 334-345: Root endpoint
@app.get("/")
async def root():
    return {"message": "Minecraft Mod Generator API"}

# Lines 348-376: Generate mod endpoint
@app.post("/api/generate-mod")
async def generate_mod(request: ItemPromptRequest, background_tasks: BackgroundTasks):
    """
    Start a new mod generation job.
    Returns job_id immediately for polling.
    """
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "progress": 0, "logs": []}

    background_tasks.add_task(run_generation_task, job_id, request.model_dump())

    return {"success": True, "jobId": job_id}

# Lines 380-386: Status endpoint
@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get current job status for frontend polling"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

# Lines 389-401: Download endpoint
@app.get("/downloads/{filename}")
async def download_mod(filename: str):
    """Serve compiled .jar files"""
    file_path = DOWNLOADS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=filename)

# Lines 414-467: Image selection endpoint
@app.post("/api/jobs/{job_id}/select-image")
async def select_image(job_id: str, selection: dict, background_tasks: BackgroundTasks):
    """
    User selects a texture option.

    Flow:
    1. Store selection: jobs[job_id]["selections"][assetType] = base64_image
    2. Check if all assets selected
    3. If complete, resume generation
    """
    asset_type = selection["assetType"]
    selected_index = selection["selectedIndex"]

    # Store selection
    selected_image = pending[asset_type]["options"][selected_index]
    jobs[job_id]["selections"][asset_type] = selected_image

    # Check if all complete
    if set(pending_types) == set(selected_types):
        jobs[job_id]["status"] = "generating"
        background_tasks.add_task(continue_generation_after_selection, job_id)

# Lines 470-537: Regenerate images endpoint
@app.post("/api/jobs/{job_id}/regenerate-images")
async def regenerate_images(job_id: str, request: dict):
    """
    User not satisfied with texture options.
    Generate 5 new options for specific asset type.
    """
    asset_type = request["assetType"]

    image_gen = ImageGenerator()
    new_images = image_gen.generate_multiple_item_textures(...)

    # Replace options
    pending[asset_type]["options"] = new_images

# Lines 540-562: Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
```

---

### `agents/langchain_agents.py` - Multi-Agent System

**Key sections**:

```python
# Lines 20-28: Shared LLM builder
def _build_llm(temperature=0.7):
    return ChatGoogleGenerativeAI(
        google_api_key=GEMINI_API_KEY,
        model="gemini-1.5-flash",
        temperature=temperature
    )

# Lines 46-79: Pydantic schemas (data contracts)
class ItemPropertiesSpec(BaseModel):
    max_stack_size: int = Field(..., ge=1, le=64)
    rarity: str = Field(..., description="COMMON, UNCOMMON, RARE, or EPIC")
    fireproof: bool
    creative_tab: str
    special_ability: str

class ItemSpec(BaseModel):
    mod_name: str
    mod_id: str
    item_name: str
    item_id: str
    description: str
    interaction_hooks: List[str] = Field(default_factory=list)
    clarifying_question: Optional[str] = None
    properties: ItemPropertiesSpec

# Lines 141-196: InteractiveItemAgent
class InteractiveItemAgent:
    """
    Conversational agent that designs items.
    Uses Pydantic to force structured JSON output.
    """
    def __init__(self, llm):
        self.llm = llm
        self.parser = PydanticOutputParser(pydantic_object=ItemSpec)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Minecraft designer..."),
            ("human", "User request: {user_prompt}...")
        ])

    def run(self, user_prompt, conversation_history, mod_name_override):
        # Format prompt
        messages = self.prompt.format_messages(
            user_prompt=user_prompt,
            format_instructions=self.parser.get_format_instructions()
        )

        # Call LLM
        response = self.llm.invoke(messages)

        # Parse structured output
        item_spec = self.parser.parse(response.content)

        # Apply override
        if mod_name_override:
            item_spec.mod_name = mod_name_override

        return item_spec

# Lines 198-236: BlockCreationAgent
class BlockCreationAgent:
    """
    Designs companion blocks for items.
    Uses cube-all model (same texture on all faces).
    """
    def run(self, user_prompt, item_spec):
        messages = self.prompt.format_messages(
            user_prompt=user_prompt,
            item_name=item_spec.item_name,
            rarity=item_spec.properties.rarity
        )
        response = self.llm.invoke(messages)
        return self.parser.parse(response.content)

# Lines 279-379: LangChainModOrchestrator
class LangChainModOrchestrator:
    """
    Coordinates all agents and produces backwards-compatible dict.
    """
    def __init__(self):
        shared_llm = _build_llm()
        self.item_agent = InteractiveItemAgent(shared_llm)
        self.block_agent = BlockCreationAgent(shared_llm)
        self.packaging_agent = PackagingAgent(shared_llm)

    def run_pipeline(self, user_prompt, author_name, mod_name_override):
        # Stage 1: Item design
        item_spec = self.item_agent.run(
            user_prompt, None, mod_name_override
        )

        # Stage 2: Block design
        block_spec = self.block_agent.run(user_prompt, item_spec)

        # Stage 3: Packaging plan
        packaging = self.packaging_agent.run(
            user_prompt, item_spec, block_spec
        )

        # Combine into dict
        return self._compose_payload(
            user_prompt, author_name,
            item_spec, block_spec, packaging
        )

    def _compose_payload(self, ...):
        """Convert Pydantic models to dict"""
        payload = {
            "modName": item_spec.mod_name,
            "modId": item_spec.mod_id,
            "itemName": item_spec.item_name,
            "itemId": item_spec.item_id,
            "properties": {
                "maxStackSize": item_spec.properties.max_stack_size,
                ...
            },
            "block": {...} if block_spec else None,
            "tool": self._derive_tool_spec(...),
            "packagingPlan": packaging.dict()
        }
        return payload

# Lines 381-503: Tool derivation (deterministic, not AI)
def _derive_tool_spec(self, user_prompt, item_spec, block_spec):
    """
    Create tool based on item rarity (no AI needed).

    Logic:
    1. Map rarity → material/stats
       COMMON  → IRON     (durability 375)
       RARE    → DIAMOND  (durability 1561)
       EPIC    → NETHERITE (durability 2031)

    2. Infer tool type from prompt
       "sword" → SWORD
       "pickaxe" → PICKAXE
       default → PICKAXE

    3. Generate crafting recipe
       PICKAXE: ["###", " S ", " S "]
       SWORD: ["#", "#", "S"]
    """
    rarity = item_spec.properties.rarity
    tier = self._get_tier_settings(rarity)
    tool_type = self._infer_tool_type(user_prompt, item_spec)

    return {
        "toolName": f"{item_spec.item_name} {tool_type.title()}",
        "toolId": f"{item_spec.item_id}_{tool_type.lower()}",
        "properties": {
            "attackDamage": tier["attack_damage"],
            "durability": tier["durability"],
            "miningSpeed": tier["mining_speed"],
            ...
        },
        "forgingRecipe": self._build_tool_forging_recipe(...)
    }
```

---

## How Everything Connects

### Dependency Graph

```
main.py
  ├─ imports config.py
  ├─ imports models.py
  ├─ imports agents/mod_analyzer.py
  ├─ imports agents/mod_generator.py
  └─ imports agents/image_generator.py

agents/mod_analyzer.py
  ├─ imports config.py
  ├─ imports agents/langchain_agents.py
  └─ uses google.generativeai (Gemini SDK)

agents/langchain_agents.py
  ├─ imports config.py
  ├─ uses langchain_google_genai
  └─ uses langchain.prompts

agents/mod_generator.py
  ├─ imports config.py
  └─ uses Pillow (for images)

agents/image_generator.py
  └─ uses Pillow (for image generation)

config.py
  └─ reads environment variables

models.py
  └─ uses Pydantic
```

### Data Flow

```
User Prompt (string)
      ↓
ItemPromptRequest (Pydantic model)
      ↓
ModAnalyzerAgent.analyze()
      ↓
LangChainModOrchestrator.run_pipeline()
      ├─→ InteractiveItemAgent → ItemSpec (Pydantic)
      ├─→ BlockCreationAgent → BlockSpec (Pydantic)
      └─→ PackagingAgent → PackagingPlan (Pydantic)
      ↓
Composed Dict (backwards compatible)
{
    "modName": str,
    "modId": str,
    "itemName": str,
    "properties": {...},
    "block": {...},
    "tool": {...}
}
      ↓
ImageGenerator.generate_multiple_*()
      ↓
List[bytes] (PNG binary data)
      ↓
User Selection
      ↓
ModGenerator.generate_mod()
      ├─→ Create Java files
      ├─→ Create JSON files
      ├─→ Create PNG files
      ├─→ Run Gradle build
      └─→ Return .jar path
      ↓
FileResponse (downloadable .jar)
      ↓
Minecraft mod!
```

---

## Summary

The backend is a **sophisticated multi-agent AI system** that:

1. **Accepts** natural language prompts via REST API
2. **Orchestrates** multiple AI agents to make design decisions
3. **Generates** texture options for user selection
4. **Produces** complete Minecraft mod code (Java + JSON + assets)
5. **Compiles** the mod into a playable .jar file
6. **Serves** the download to the user

**Key Technologies**:
- FastAPI for async HTTP
- Google Gemini for AI decisions
- LangChain for agent orchestration
- Pydantic for data validation
- Gradle for mod compilation

**Agent Systems** (3 levels):
1. **NEW**: `decision_workflow.py` - Clean, staged JSON pipeline (not yet integrated)
2. **CURRENT**: `langchain_agents.py` - Full multi-agent with blocks/tools
3. **FALLBACK**: `mod_analyzer.py` legacy - Simple Gemini fallback

The system is designed to be **resilient** (multiple fallback layers), **extensible** (easy to add new agents), and **maintainable** (clear separation of concerns).
