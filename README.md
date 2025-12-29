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

3. **Run the startup script**
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

```
┌─────────────┐
│   Frontend  │  Simple prompt interface (Minecraft-styled)
│ (HTML/JS)   │
└──────┬──────┘
       │ HTTP POST /api/generate-mod
       ▼
┌─────────────┐
│   Backend   │  FastAPI Server
│  (Python)   │
└──────┬──────┘
       │
       ├──▶ 1. LangChain Multi-Agent Pipeline (Gemini)
       │      Stage 1: NamingAgent → mod_name, mod_id, item_name, item_id
       │      Stage 2: PropertiesAgent → rarity, stack size, etc.
       │      Stage 3: BlockAgent → companion block (optional)
       │      Stage 4: ToolAgent → companion tool (optional)
       │      Returns structured JSON specification
       │
       ├──▶ 2. ImageGenerator (Gemini)
       │      Generates 5 texture options (16x16 pixel art)
       │      User selects favorite from modal
       │
       ├──▶ 3. ModGenerator
       │      Creates Java files, assets, configs
       │      Integrates AI-generated texture
       │
       ├──▶ 4. Gradle Compiler
       │      Compiles Fabric mod → .jar file
       │
       └──▶ 5. Download
              Returns .jar to user
```

## 📁 Project Structure

```
mcmoddemo/
├── .env                           # Gemini API key (in backend/)
├── START.sh                       # Startup script
├── README.md                      # This file
├── WORKFLOW_DESIGN.md             # New structured decision pipeline architecture
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
    ├── agents/
    │   ├── decision_workflow.py   # New structured JSON pipeline
    │   ├── langchain_agents.py    # Multi-agent orchestration
    │   ├── mod_analyzer.py        # Legacy analyzer with fallbacks
    │   ├── image_generator.py     # Texture generator
    │   └── mod_generator.py       # Java/Gradle code generator
    ├── generated/                 # Temporary mod projects
    └── downloads/                 # Compiled .jar files
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

### Docker

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

## 📝 TODO

- [x] Add texture generation with DALL-E 3 ✅
- [ ] Texture style options (realistic, cartoonish, pixel perfect)
- [ ] Texture caching and reuse
- [ ] Support multiple items per mod
- [ ] Add mod testing in Docker
- [ ] User accounts and mod history
- [ ] Shareable mod links
- [ ] Advanced properties (food values, durability, enchantments)
- [ ] Block generation support
- [ ] Recipe generation
- [ ] Multi-version support (1.20.x, 1.21.x)
- [ ] Animated textures
- [ ] HD texture packs (32x32, 64x64)

## 🙏 Credits

- **Fabric**: Lightweight Minecraft modding framework
- **Google Gemini**: Advanced AI for multi-agent decisions and texture generation
- **LangChain**: Multi-agent orchestration framework
- **FastAPI**: Modern Python web framework
- **Pydantic**: Data validation and structured outputs

## 📄 License

MIT License

---

**Made with ❤️ for the Minecraft modding community**

Enjoy creating mods! 🎮✨
