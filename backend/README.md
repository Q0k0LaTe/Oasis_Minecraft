## Minecraft Mod Generator - AI Backend

LangChain + OpenAI powered backend for generating Minecraft Fabric 1.21 mods.

## 🏗️ Architecture

```
User Prompt → AI Analyzer → Mod Generator → Gradle Compiler → .jar Download
```

### Workflow

1. **AI Analysis** (LangChain + OpenAI)
   - Analyzes user's natural language prompt
   - Decides mod name, item properties, rarity, etc.
   - Returns structured specification

2. **Code Generation**
   - Generates complete Fabric mod structure
   - Creates Java files, JSON configs, assets
   - Sets up Gradle build system

3. **Compilation**
   - Runs Gradle build
   - Compiles Java code
   - Packages as .jar file

4. **Delivery**
   - Moves .jar to downloads directory
   - Returns download URL to frontend

## 📁 Structure

```
backend/
├── main.py                    # FastAPI server
├── config.py                  # Configuration
├── models.py                  # Pydantic models
├── requirements.txt           # Python dependencies
├── agents/
│   ├── mod_analyzer.py       # AI prompt analyzer (LangChain)
│   └── mod_generator.py      # Mod code generator
├── generated/                 # Temporary mod projects
└── downloads/                 # Compiled .jar files
```

## 🚀 Setup

### 1. Install Python Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

The `.env` file in the project root should contain:

```
OPENAI_API_KEY=sk-...
```

Optional overrides (helpful if your Minecraft/Fabric install uses a newer release):

```
MINECRAFT_VERSION=1.21.5
FABRIC_LOADER_VERSION=0.16.13
FABRIC_API_VERSION=0.128.2+1.21.5
YARN_MAPPINGS=1.21.5+build.1
```

These values flow directly into the generated Gradle project (`fabric.mod.json`, `gradle.properties`, etc.), so match them to the versions reported by your Fabric loader to avoid in-game crashes. If you change `MINECRAFT_VERSION`, either set `FABRIC_API_VERSION` yourself or use one of the bundled mappings:

| Minecraft | Fabric API suggestion      |
|-----------|----------------------------|
| `1.21`    | `0.102.0+1.21`             |
| `1.21.1`  | `0.105.0+1.21.1`           |
| `1.21.5`  | `0.128.2+1.21.5` (default) |

If your version isn't listed, set `FABRIC_API_VERSION` manually to the exact artifact published on https://maven.fabricmc.net/.

### 3. Install Java & Gradle

Required for compiling mods:

```bash
# macOS
brew install openjdk@21 gradle

# Ubuntu/Debian
sudo apt install openjdk-21-jdk gradle

# Windows
# Download from https://adoptium.net/ and https://gradle.org/
```

Verify installation:
```bash
java -version  # Should be 21+
gradle -version  # Should be 8.0+
```

## 🎯 Running the Backend

```bash
cd backend
python main.py
```

The server will start on `http://localhost:3000`

**Endpoints:**
- `GET /` - API info
- `POST /api/generate-mod` - Generate mod
- `GET /api/status/{job_id}` - Check job status
- `GET /downloads/{filename}` - Download mod
- `GET /docs` - API documentation (Swagger UI)

## 🤖 AI Agent Details

### ModAnalyzerAgent

Uses **LangChain** with **OpenAI GPT-4o** to:
- Parse natural language prompts
- Extract item concepts
- Decide technical properties
- Generate valid IDs
- Provide reasoning

**Example Input:**
```
"A glowing ruby gem that's rare and valuable"
```

**Example Output:**
```json
{
  "modName": "Ruby Gem Mod",
  "modId": "rubygemmod",
  "itemName": "Ruby Gem",
  "itemId": "ruby_gem",
  "properties": {
    "maxStackSize": 16,
    "rarity": "RARE",
    "fireproof": false,
    "creativeTab": "INGREDIENTS"
  },
  "reasoning": "Rare gem → RARE rarity, stack of 16"
}
```

**Prompt Engineering:**
- System prompt defines Minecraft mod design expertise
- Structured output using Pydantic parser
- Fallback logic for API failures
- ID validation and sanitization

### ModGenerator

Generates complete Fabric mod:

1. **Directory Structure**
   ```
   mod-project/
   ├── src/main/java/          # Java source
   ├── src/main/resources/     # Assets, configs
   ├── src/client/java/        # Client code
   ├── build.gradle
   └── gradle.properties
   ```

2. **Generated Files**
   - `MainMod.java` - Mod initializer
   - `ModItems.java` - Item registration
   - `ModClient.java` - Client entrypoint
   - `fabric.mod.json` - Mod metadata
   - `en_us.json` - Translations
   - `item_model.json` - 3D model
   - `texture.png` - Item texture

3. **Compilation**
   - Runs `./gradlew build`
   - 5-minute timeout
   - Captures output for debugging
   - Returns path to .jar file

## 📡 API Usage

### Generate Mod

```bash
curl -X POST http://localhost:3000/api/generate-mod \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A powerful diamond sword",
    "authorName": "PlayerName",
    "modName": null
  }'
```

**Response:**
```json
{
  "success": true,
  "jobId": "uuid-here",
  "aiDecisions": {
    "modName": "Diamond Sword Mod",
    "modId": "diamondswordmod",
    "itemName": "Diamond Sword",
    "itemId": "diamond_sword",
    "description": "A powerful diamond sword",
    "author": "PlayerName",
    "properties": {
      "maxStackSize": 1,
      "rarity": "EPIC",
      "fireproof": false,
      "creativeTab": "COMBAT"
    }
  },
  "downloadUrl": "/downloads/diamondswordmod.jar",
  "message": "Mod generated successfully!"
}
```

### Download Mod

```bash
curl -O http://localhost:3000/downloads/diamondswordmod.jar
```

## ⚙️ Configuration

Edit `config.py`:

```python
# AI Model (gpt-4o is the latest and most powerful)
AI_MODEL = "gpt-4o"

# AI Temperature (0.7 = creative but consistent)
AI_TEMPERATURE = 0.7

# Minecraft/Fabric Versions
MINECRAFT_VERSION = "1.21"
FABRIC_LOADER_VERSION = "0.15.11"
FABRIC_API_VERSION = "0.99.4+1.21"
```

## 🔧 Troubleshooting

### "OPENAI_API_KEY not found"
- Ensure `.env` file exists in project root
- Check the API key is valid
- Restart the server after adding the key

### "Gradle build failed"
- Ensure Java 21+ is installed
- Check Gradle is accessible via PATH
- Review build logs in console
- Verify internet connection (downloads dependencies)

### "No module named 'langchain'"
- Activate virtual environment
- Run `pip install -r requirements.txt`
- Check Python version is 3.10+

### Compilation Takes Too Long
- First build downloads dependencies (~5-10 minutes)
- Subsequent builds are faster (~30 seconds)
- Increase timeout in `mod_generator.py` if needed

## 🔬 Testing

### Test AI Agent

```python
from agents.mod_analyzer import ModAnalyzerAgent

agent = ModAnalyzerAgent()
result = agent.analyze("A rare ruby gem")
print(result)
```

### Test Mod Generator

```python
from agents.mod_generator import ModGenerator

generator = ModGenerator()
spec = {
    "modId": "testmod",
    "modName": "Test Mod",
    "itemId": "test_item",
    "itemName": "Test Item",
    "author": "Tester",
    "description": "Test",
    "properties": {
        "maxStackSize": 64,
        "rarity": "COMMON",
        "fireproof": False,
        "creativeTab": "INGREDIENTS"
    }
}
result = generator.generate_mod(spec, "test-job")
print(result)
```

## 📊 Performance

- **AI Analysis:** ~1-3 seconds
- **Code Generation:** <1 second
- **First Compilation:** ~5-10 minutes (downloads dependencies)
- **Subsequent Compilations:** ~30-60 seconds
- **Total First Request:** ~5-10 minutes
- **Total Subsequent Requests:** ~30-60 seconds

## 🚀 Production Deployment

### Optimization Tips

1. **Pre-build Dependencies**
   - Create a template project
   - Pre-download Fabric dependencies
   - Copy template instead of fresh build

2. **Caching**
   - Cache AI responses for common prompts
   - Reuse compiled artifacts
   - Use Redis for job tracking

3. **Async Processing**
   - Move compilation to background workers
   - Use Celery or RQ for task queue
   - Return job ID immediately

4. **Resource Limits**
   - Limit concurrent builds
   - Set max job duration
   - Clean up old generated files

### Environment Variables

```bash
export OPENAI_API_KEY="sk-..."
export HOST="0.0.0.0"
export PORT="3000"
export AI_MODEL="gpt-4o-mini"
```

### Docker Deployment

```dockerfile
FROM python:3.11
RUN apt-get update && apt-get install -y openjdk-21-jdk gradle
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

## 📚 Dependencies

- **fastapi** - Web framework
- **uvicorn** - ASGI server
- **langchain** - AI orchestration
- **langchain-openai** - OpenAI integration
- **openai** - OpenAI API client
- **pydantic** - Data validation
- **Jinja2** - Template engine
- **python-dotenv** - Environment variables

## 🔐 Security

- Never commit `.env` file
- Validate all user inputs
- Sanitize file paths
- Limit file sizes
- Rate limit API requests (see below)
- Scan generated code for malicious patterns

### IP Rate Limiting

The API includes built-in IP-based rate limiting to protect against abuse and DDoS attacks.

#### Default Limits

| Tier | Limit | Window | Description |
|------|-------|--------|-------------|
| **Global** | 30 requests | 10 seconds | Sustained rate for all endpoints |
| **Burst** | 10 requests | 1 second | Prevents sudden spikes |
| **Auth** | 10 requests | 60 seconds | Login, register, verification |
| **Verification** | 3 requests | 60 seconds | Send verification code (email protection) |
| **Resource** | 5 requests | 60 seconds | Build, AI generation (CPU-intensive) |

#### Excluded Paths

These paths are not rate limited:
- `/docs`, `/redoc`, `/openapi.json` (API documentation)
- `/api/health` (health checks)

#### Response Headers

All responses include rate limit headers:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in window
- `X-RateLimit-Reset`: Unix timestamp when window resets
- `Retry-After`: Seconds to wait (only on 429 responses)

#### 429 Response Format

```json
{
  "detail": "Too many requests. Please slow down.",
  "error": "rate_limit_exceeded",
  "retry_after_seconds": 10,
  "limit": 30,
  "tier": "global"
}
```

#### Environment Variables

```bash
# Global limits
RATE_LIMIT_GLOBAL_MAX=30        # Max requests per window
RATE_LIMIT_GLOBAL_WINDOW=10     # Window in seconds

# Burst limits
RATE_LIMIT_BURST_MAX=10         # Max requests per burst window
RATE_LIMIT_BURST_WINDOW=1       # Burst window in seconds

# Auth endpoint limits
RATE_LIMIT_AUTH_MAX=10
RATE_LIMIT_AUTH_WINDOW=60

# Verification code limits (strict)
RATE_LIMIT_VERIFICATION_MAX=3
RATE_LIMIT_VERIFICATION_WINDOW=60

# Resource-intensive endpoints
RATE_LIMIT_RESOURCE_MAX=5
RATE_LIMIT_RESOURCE_WINDOW=60

# Excluded paths (comma-separated)
RATE_LIMIT_EXCLUDE_PATHS=/docs,/redoc,/openapi.json,/api/health,/

# Whitelist IPs (comma-separated, supports CIDR)
RATE_LIMIT_WHITELIST_IPS=127.0.0.1,::1

# Fail mode when Redis is unavailable: "closed" (deny) or "open" (allow)
# Default: "closed" in production, "open" in development
RATE_LIMIT_FAIL_MODE=closed
```

#### Testing Rate Limits

```bash
# Run the stress test script
chmod +x tests/test_rate_limit_stress.sh
./tests/test_rate_limit_stress.sh http://localhost:3000

# Or manually with curl loop
for i in {1..20}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/
done
```

#### Implementation Details

- **Atomic operations**: Uses Redis Lua scripts to prevent race conditions
- **Multi-tier**: Checks burst limit first, then global limit
- **Path-specific**: High-risk endpoints have stricter limits
- **Fail-safe**: Uses local in-memory fallback when Redis is unavailable
- **Whitelist**: Configurable IP whitelist for trusted sources

## 📝 License

MIT License - Part of AI Minecraft Mod Generator project
