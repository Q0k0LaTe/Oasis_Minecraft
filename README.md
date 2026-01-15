# 🎮 AI Minecraft Mod Generator

Generate custom Minecraft Fabric 1.21 mods using natural language! Just describe what item you want, and AI creates a complete, working mod for you.

## ✨ Features

- 🤖 **AI-Powered** - Powered by Google Gemini with LangChain multi-agent orchestration
- 💬 **Natural Language** - Just describe your item in plain English
- 🎯 **Smart Decisions** - Structured JSON workflow with dedicated agents for naming, properties, blocks, and tools
- 🎨 **AI-Generated Textures** - Choose from 5 AI-generated texture options per asset
- ⚡ **Complete Mods** - Generates full Fabric mod with Java code, assets, and build system
- 📦 **Ready to Play** - Download compiled .jar file and drop into your mods folder
- 🖼️ **Minecraft UI** - Authentic pixelated Minecraft-style interface

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Gemini API Key
- (Optional) Java 21+ and Gradle 8.0+ for mod compilation

### Installation

1. **Clone the repository**
```bash
git clone <your-repo>
cd mcmoddemo
```

2. **Set up environment variables**
```bash
# Create .env file in backend/
cd backend
echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
```

~~3. Run the startup script~~
```bash
./START.sh
```


That's it! The script will:
- Create a virtual environment
- Install all dependencies
- Start the backend server (port 3000)
- Start the frontend server (port 8000)
- Open your browser automatically

### Access the App

- **Frontend**: http://localhost:8000
- **Backend API**: http://localhost:3000
- **API Docs**: http://localhost:3000/docs
- **V2 API Endpoint**: http://localhost:3000/api/v2/generate (recommended)

## 🎮 How to Use

### 1. Describe Your Item

Type a description in the text box:
```
"A glowing ruby gem that's rare and valuable"
```

### 2. Generate

Click **"Generate Mod"** or press `Ctrl+Enter`

### 3. Wait

Watch the AI work:
- ○ Analyzing your prompt...
- ○ AI is deciding item properties...
- ○ Generating mod structure...
- ○ Creating Java files...
- ○ Generating assets...
- ○ Compiling mod...

### 4. Download

Download your `.jar` file and place it in:
```
.minecraft/mods/
```

### 5. Play!

Launch Minecraft 1.21 with Fabric and enjoy your custom item!

## 💡 Example Prompts

| Prompt | Result |
|--------|--------|
| "A glowing blue crystal that's rare and magical" | Rare crystal in Ingredients tab |
| "A powerful diamond sword with extra damage" | Epic sword in Combat tab, max stack 1 |
| "A golden apple that heals you when eaten" | Food item in Food & Drink tab |
| "A fireball staff that never burns" | Fireproof staff in Tools tab |
| "A rare emerald shard used for crafting" | Rare ingredient, stack of 16 |

## 🏗️ Architecture

### V2 Architecture (Recommended - Compiler-Style Pipeline)

The new V2 architecture follows compiler design patterns for reliability and debuggability:

```
┌─────────────┐
│   Frontend  │  Minecraft-styled UI
│ (HTML/JS)   │
└──────┬──────┘
       │ HTTP POST /api/v2/generate
       ▼
┌─────────────────────────────────────────────────────────┐
│                    Backend Pipeline                      │
│                                                          │
│  User Prompt                                            │
│       │                                                  │
│       ▼                                                  │
│  1. Orchestrator ──────▶ Converts prompt to SpecDelta   │
│       │                  (LLM reasoning happens here)   │
│       ▼                                                  │
│  2. SpecManager ───────▶ Applies delta to canonical spec│
│       │                  (Versioned, persistent)        │
│       ▼                                                  │
│  3. Compiler ──────────▶ Transforms Spec → IR           │
│       │                  (Fills defaults, generates IDs)│
│       ▼                                                  │
│  4. Planner ───────────▶ Builds Task DAG from IR        │
│       │                  (Dependency graph)             │
│       ▼                                                  │
│  5. Executor ──────────▶ Runs tasks using tools         │
│       │                  (Deterministic generation)     │
│       ▼                                                  │
│  6. Validator ─────────▶ Pre-build validation           │
│       │                  (Checks for errors)            │
│       ▼                                                  │
│  7. Builder ───────────▶ Gradle compilation              │
│       │                  (Produces JAR)                 │
│       ▼                                                  │
│  8. Error Fixer ───────▶ Deterministic error patches    │
│                          (If needed)                     │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
                   .jar file
```

**Key Principles:**
1. **Spec is for humans. IR is for machines.** - Clear separation of concerns
2. **No code generation without IR.** - All generation flows through fully specified IR
3. **Generators must be dumb and deterministic.** - Same input always produces same output
4. **All reasoning happens before execution.** - Orchestrator/Compiler handle AI, Executor is mechanical
5. **Errors trigger patches, not retries.** - Deterministic error fixing

### V1 Architecture (Legacy - For Reference)

```
┌─────────────┐
│   Frontend  │
│ (HTML/JS)   │
└──────┬──────┘
       │ HTTP POST /api/generate-mod (Legacy V1)
       ▼
┌─────────────┐
│   Backend   │
│  (Python)   │
└──────┬──────┘
       │
       ├──▶ 1. LangChain Multi-Agent Pipeline (Gemini)
       │      Directly generates code (no IR)
       │
       ├──▶ 2. ImageGenerator (Gemini)
       │      5 texture options
       │
       ├──▶ 3. ModGenerator
       │      Monolithic generator
       │
       └──▶ 4. Gradle Compiler
```

**Note:** V1 API (`/api/generate-mod`) is maintained for backward compatibility. All new features use V2 (`/api/v2/generate`).

## 📁 Project Structure

```
mcmoddemo/
├── .env                           # Gemini API key (in backend/)
├── START.sh                       # Startup script
├── README.md                      # This file
├── WORKFLOW_DESIGN.md             # Architecture design document
├── AGENT_RESTRUCTURE_PLAN.md      # Migration plan
├── AGENT_RESTRUCTURE_STATUS.md    # Implementation status
│
├── frontend/                      # Web interface
│   ├── index.html                 # Main page
│   ├── assets/
│   │   ├── css/style.css         # Minecraft styling
│   │   └── js/script.js          # Frontend logic
│   └── README.md
│
└── backend/                       # Python backend
    ├── main.py                    # FastAPI server
    ├── config.py                  # Configuration
    ├── models.py                  # Data models
    ├── requirements.txt           # Dependencies
    │
    ├── agents/                    # NEW: V2 Architecture
    │   ├── pipeline.py           # 🆕 Main pipeline orchestrator
    │   │
    │   ├── core/                 # 🆕 Core components
    │   │   ├── orchestrator.py   # Prompt → SpecDelta
    │   │   ├── spec_manager.py   # Canonical spec with versioning
    │   │   ├── compiler.py       # Spec → IR transformation
    │   │   ├── planner.py        # IR → Task DAG
    │   │   ├── executor.py       # Task execution engine
    │   │   ├── validator.py      # Pre-build validation
    │   │   ├── builder.py        # Gradle compilation
    │   │   └── error_fixer.py    # Error interpretation & fixing
    │   │
    │   ├── tools/                # 🆕 Tool implementations
    │   │   ├── tool_registry.py  # Central tool registry
    │   │   ├── workspace_tool.py # Directory structure
    │   │   ├── gradle_tool.py    # Build configuration
    │   │   ├── fabric_json_tool.py # Mod metadata
    │   │   ├── java_code_tool.py # Java code generation
    │   │   ├── asset_tool.py     # Asset generation
    │   │   ├── mixins_tool.py    # Mixins config
    │   │   ├── gradle_wrapper_tool.py # Gradle wrapper
    │   │   ├── build_tool.py     # Compilation
    │   │   ├── image_generator.py # AI texture generation
    │   │   └── reference_selector.py # Texture reference AI
    │   │
    │   ├── schemas/              # 🆕 Data schemas
    │   │   ├── spec_schema.py    # User intent format (ModSpec)
    │   │   ├── ir_schema.py      # Machine blueprint (ModIR)
    │   │   └── task_schema.py    # Execution plan (TaskDAG)
    │   │
    │   ├── _archive/             # 🗄️ Legacy files (V1)
    │   │   ├── langchain_agents.py # Old multi-agent system
    │   │   └── mod_analyzer.py   # Old analyzer
    │   │
    │   ├── mod_generator.py      # ⚠️ Legacy (V1 API only)
    │   └── __init__.py           # Exports V1 + V2 components
    │
    ├── routers/
    │   ├── jobs.py               # V1 API endpoints (legacy)
    │   ├── jobs_v2.py            # 🆕 V2 API endpoints (recommended)
    │   ├── auth.py               # Authentication
    │   └── sessions.py           # Session management
    │
    ├── tests/                    # 🆕 Test suite
    │   ├── agents/
    │   │   ├── test_pipeline.py  # Pipeline integration tests
    │   │   ├── test_compiler.py  # Compiler unit tests
    │   │   ├── test_spec_manager.py # SpecManager tests
    │   │   └── test_tools.py     # Tool tests
    │   └── README.md
    │
    ├── generated/                # Temporary mod projects
    └── downloads/                # Compiled .jar files
```

## 🤖 AI Workflow

### 1. Multi-Stage Decision Pipeline (Gemini + LangChain)

```python
User: "A rare ruby gem"
↓
Stage 1 - NamingAgent:
- mod_name: "Ruby Gems Mod"
- mod_id: "rubygemsmod"
- item_name: "Ruby Gem"
- item_id: "ruby_gem"
↓
Stage 2 - PropertiesAgent:
- rarity: "RARE"
- max_stack_size: 16
- creative_tab: "INGREDIENTS"
- fireproof: false
↓
Stage 3 - BlockAgent (optional):
- Generates companion storage block
↓
Stage 4 - ToolAgent (optional):
- Generates mining tool/weapon
↓
Returns UnifiedModDecision (structured JSON)
```

### 2. Texture Generation (Gemini)

```
Specification + Description
↓
ImageGenerator:
- Generates 5 different 16x16 texture options
- Each optimized for Minecraft pixel art style
↓
Frontend Modal:
- User selects favorite texture
- Option to regenerate 5 more if unsatisfied
↓
Selected texture → continues to code generation
```

### 3. Code Generation

```
Specification + AI Texture
↓
Generate Files:
- MainMod.java (Mod initializer)
- ModItems.java (Item registration)
- fabric.mod.json (Mod metadata)
- en_us.json (Translations)
- item_model.json (3D model)
- texture.png (AI-generated pixel art)
- build.gradle (Build config)
↓
Complete Fabric Mod Structure
```

### 4. Compilation

```
Fabric Mod Project
↓
Run: ./gradlew build
↓
Output: modname.jar
↓
Move to: downloads/
```

## ⚙️ Configuration

### Backend (`backend/config.py`)

```python
# AI Configuration - Google Gemini
GEMINI_API_KEY = "your_api_key"
AI_MODEL = "gemini-1.5-flash"
AI_TEMPERATURE = 0.7             # Creative but consistent

# Minecraft Versions
MINECRAFT_VERSION = "1.21"
FABRIC_LOADER_VERSION = "0.15.11"
FABRIC_API_VERSION = "0.99.4+1.21"
JAVA_VERSION = "21"
```

### Frontend (`frontend/assets/js/script.js`)

```javascript
const API_BASE_URL = 'http://localhost:3000/api';
```

## 🔧 Development

### Backend Development

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Frontend Development

```bash
cd frontend
python3 -m http.server 8000
```

### API Documentation

Once backend is running, visit:
- http://localhost:3000/docs (Swagger UI)
- http://localhost:3000/redoc (ReDoc)

## 📊 Performance

- **Gemini Multi-Agent Pipeline**: ~3-6 seconds
- **Texture Generation (5 options)**: ~5-10 seconds per asset type
- **Code Generation**: <1 second
- **First Compilation**: ~5-10 minutes (downloads dependencies)
- **Subsequent Compilations**: ~30-60 seconds
- **Total**: Variable depending on texture selections

### Cost per Mod

| Component | Cost |
|-----------|------|
| Gemini Analysis (multi-stage) | ~$0.01-$0.03 |
| Texture Generation (5 options × assets) | ~$0.02-$0.05 |
| **Total** | **~$0.03-$0.08** |

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check Python version
python3 --version  # Should be 3.11+

# Check API key
cat backend/.env  # Should contain GEMINI_API_KEY

# Install dependencies
cd backend
pip install -r requirements.txt
```

### Compilation fails

```bash
# Check Java version
java -version  # Should be 21+

# Check Gradle
gradle -version  # Should be 8.0+

# macOS: Install via Homebrew
brew install openjdk@21 gradle

# Ubuntu/Debian
sudo apt install openjdk-21-jdk gradle
```

### Frontend can't connect to backend

1. Check backend is running on port 3000
2. Check CORS settings in `backend/config.py`
3. Try `http://127.0.0.1:8000` instead of `localhost`

## 🚀 Production Deployment

### Docker Compose (Backend-focused)

Use the provided `docker-compose.yml` to run the backend with Postgres + Redis:

```bash
# Create backend/.env from the template and fill in required keys
cp backend/.env.example backend/.env

# Start services
docker compose up --build
```

Services and ports:
- API: http://localhost:3000
- Postgres: 5432
- Redis: 6379

Notes:
- `backend/.env` must include `GEMINI_API_KEY`, `OPENAI_API_KEY`, and `RESEND_API_KEY`.
- Generated files map to `backend/generated` and `backend/downloads` on the host.
- TODO: Add Java 21 + Gradle to the backend Docker image for in-container mod compilation.

### Docker (single container)

```dockerfile
FROM python:3.11
RUN apt-get update && apt-get install -y openjdk-21-jdk gradle
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "backend/main.py"]
```

### Environment Variables

```bash
export GEMINI_API_KEY="your_key_here"
export HOST="0.0.0.0"
export PORT="3000"

# Optional: override Minecraft/Fabric targets (defaults target Minecraft 1.21.5)
export MINECRAFT_VERSION="1.21.5"
export FABRIC_LOADER_VERSION="0.16.13"
export FABRIC_API_VERSION="0.128.2+1.21.5"  # Required when you change the MC version
export YARN_MAPPINGS="1.21.5+build.1"
```

If you change `MINECRAFT_VERSION`, either set `FABRIC_API_VERSION` yourself or use one of the baked-in combos:

| Minecraft | Fabric API suggestion      |
|-----------|----------------------------|
| `1.21`    | `0.102.0+1.21`             |
| `1.21.1`  | `0.105.0+1.21.1`           |
| `1.21.5`  | `0.128.2+1.21.5` (default) |

The backend will warn if it can't match your Minecraft version—set `FABRIC_API_VERSION` explicitly in that case.

## 📝 Recent Updates

### ✅ V2 Architecture (January 2026)
- [x] Complete pipeline restructure following compiler design patterns
- [x] Spec → IR → Task DAG architecture
- [x] Tool registry system
- [x] Deterministic code generation
- [x] Comprehensive test suite
- [x] V2 API endpoints (`/api/v2/generate`)
- [x] AI-powered texture generation with Gemini 3 Pro
- [x] 5-variant texture selection workflow
- [x] Reference texture AI selection

### 🚧 TODO

- [ ] Migrate V1 features to V2 pipeline
- [ ] Interactive texture selection in V2 API
- [ ] Texture style options (realistic, cartoonish, pixel perfect)
- [ ] Texture caching and reuse
- [ ] Support multiple items per mod
- [ ] Add mod testing in Docker
- [ ] User accounts and mod history
- [ ] Shareable mod links
- [ ] Advanced properties (food values, durability, enchantments)
- [ ] Enhanced block generation support
- [ ] Recipe generation
- [ ] Multi-version support (1.20.x, 1.21.x)
- [ ] Animated textures
- [ ] HD texture packs (32x32, 64x64)

## 🧪 Testing

Run the test suite:

```bash
cd backend
pytest

# With coverage
pytest --cov=agents --cov-report=html

# Run specific test
pytest tests/agents/test_pipeline.py -v
```

## 📚 Documentation

- **[WORKFLOW_DESIGN.md](WORKFLOW_DESIGN.md)** - Complete architecture design and principles
- **[AGENT_RESTRUCTURE_PLAN.md](AGENT_RESTRUCTURE_PLAN.md)** - Migration plan from V1 to V2
- **[AGENT_RESTRUCTURE_STATUS.md](AGENT_RESTRUCTURE_STATUS.md)** - Implementation progress
- **[RESTRUCTURE_COMPLETE.md](RESTRUCTURE_COMPLETE.md)** - Final implementation summary
- **[backend/tests/README.md](backend/tests/README.md)** - Testing guide

## 🙏 Credits

- **Fabric**: Lightweight Minecraft modding framework
- **Google Gemini**: Advanced AI for multi-agent decisions and texture generation
- **LangChain**: Multi-agent orchestration framework
- **FastAPI**: Modern Python web framework
- **Pydantic**: Data validation and structured outputs

## 📄 License

© 2026 <Team Name>. All rights reserved.

---

**Made with ❤️ for the Minecraft modding community**

<a href="https://github.com/TheCYPER/Oasis_Minecraft/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=TheCYPER/Oasis_Minecraft" />
</a>

Made with [contrib.rocks](https://contrib.rocks).

Enjoy creating mods! 🎮✨
