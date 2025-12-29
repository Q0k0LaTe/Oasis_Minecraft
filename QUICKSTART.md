# 🚀 Quick Start Guide

Get your AI Minecraft Mod Generator running in 5 minutes!

## ⚡ Super Quick Start

```bash
# 1. Make sure you have the OpenAI API key in .env file
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# 2. Run the startup script
./START.sh

# 3. Open your browser
# Frontend: http://localhost:8000
# Backend: http://localhost:3000
```

That's it! 🎉

## 📋 Prerequisites

Before you start, make sure you have:

### Required
- ✅ **Python 3.10+** - `python3 --version`
- ✅ **Java 21+** - `java -version`
- ✅ **Gradle 8.0+** - `gradle -version`
- ✅ **OpenAI API Key** - Get from https://platform.openai.com/api-keys

### Install Missing Requirements

**macOS:**
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Java and Gradle
brew install openjdk@21 gradle

# Install Python (if needed)
brew install python@3.11
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y openjdk-21-jdk gradle python3.11 python3.11-venv python3-pip
```

**Windows:**
1. Install Python from https://www.python.org/downloads/
2. Install Java from https://adoptium.net/
3. Install Gradle from https://gradle.org/install/

## 🎯 Step-by-Step Setup

### 1. Get an OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-`)

### 2. Set Up Environment

```bash
cd mcmoddemo

# Create .env file with your API key
echo "OPENAI_API_KEY=sk-your-actual-key-here" > .env
```

### 3. Install Backend Dependencies

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

cd ..
```

### 4. Start the Servers

**Option A: Use the startup script (Recommended)**
```bash
./START.sh
```

**Option B: Manual start**
```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
python main.py

# Terminal 2: Frontend
cd frontend
python3 -m http.server 8000
```

### 5. Open in Browser

- **Frontend**: http://localhost:8000
- **Backend API Docs**: http://localhost:3000/docs

## 🎮 Create Your First Mod

1. **Enter a prompt** in the text box:
   ```
   A glowing ruby gem that's rare and valuable
   ```

2. **Click "Generate Mod"** (or press Ctrl+Enter)

3. **Wait ~30-60 seconds** (first time may take 5-10 minutes due to dependency downloads)

4. **Download** the `.jar` file

5. **Install the mod**:
   - Copy the `.jar` to `.minecraft/mods/` folder
   - Make sure you have Fabric Loader 0.15.11+ and Fabric API installed
   - Launch Minecraft 1.21

6. **Play!** Find your item in the creative inventory

## 💡 Example Prompts to Try

```
A powerful diamond sword with fire damage
```

```
A magical staff that shoots lightning
```

```
A golden apple that grants regeneration
```

```
A dragon scale that's fireproof and epic rarity
```

```
A mysterious orb that glows in the dark
```

## 🔧 Troubleshooting

### "OPENAI_API_KEY not found"

```bash
# Check if .env file exists
cat .env

# Should show: OPENAI_API_KEY=sk-...

# If not, create it:
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

### "Module not found" errors

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### "Java not found" or "Gradle not found"

```bash
# macOS
brew install openjdk@21 gradle

# Ubuntu
sudo apt install openjdk-21-jdk gradle

# Verify
java -version  # Should show version 21+
gradle -version  # Should show version 8.0+
```

### Backend won't start

```bash
# Check Python version
python3 --version  # Should be 3.10+

# Try activating venv first
cd backend
source venv/bin/activate
python main.py
```

### First compilation takes forever

This is normal! The first build downloads all Fabric dependencies (~500MB). This can take 5-10 minutes. Subsequent builds will be much faster (~30-60 seconds).

### Mod doesn't load in Minecraft

Make sure you have:
1. Fabric Loader 0.15.11+ installed
2. Fabric API mod installed
3. Minecraft 1.21 (not 1.20.x or 1.21.x)
4. The mod .jar file in `.minecraft/mods/` folder

## 🌐 API Endpoints

Once backend is running:

- `GET /` - API information
- `POST /api/generate-mod` - Generate a mod
- `GET /api/status/{job_id}` - Check job status
- `GET /downloads/{filename}` - Download mod file
- `GET /docs` - Interactive API documentation
- `GET /api/health` - Health check

## 📊 What to Expect

### First Mod Generation
- AI Analysis: ~2-3 seconds
- Code Generation: <1 second
- Compilation: ~5-10 minutes (first time only!)
- **Total: ~5-10 minutes**

### Subsequent Mod Generations
- AI Analysis: ~2-3 seconds
- Code Generation: <1 second
- Compilation: ~30-60 seconds
- **Total: ~30-60 seconds**

## 🎨 Frontend Features

- **Simple Prompt Input** - Just describe what you want
- **Example Chips** - Click to try pre-made prompts
- **Advanced Options** - Override author name or mod name
- **Real-time Progress** - See each step of generation
- **AI Analysis Preview** - Review AI's decisions
- **One-Click Download** - Get your .jar file instantly

## 🔒 Security Notes

- **Never commit .env file** - It contains your API key
- **Never share your API key** - Keep it secret
- **Monitor API usage** - OpenAI charges per token
- **Set spending limits** - In OpenAI dashboard

## 💰 Cost Estimates

Using GPT-4o (most powerful):
- **Per mod**: ~$0.01 - $0.03
- **100 mods**: ~$1 - $3
- **1000 mods**: ~$10 - $30

Still very affordable! 🎉

**Cost Savings Tip:** If you want to reduce costs, edit `backend/config.py` and change `AI_MODEL = "gpt-4o"` to `AI_MODEL = "gpt-4o-mini"` (10x cheaper, still great results!)

## 📚 Next Steps

Once everything is working:

1. **Try different prompts** - Get creative!
2. **Read the full README.md** - Learn about architecture
3. **Check backend/README.md** - Deep dive into AI agent
4. **Explore API docs** - http://localhost:3000/docs
5. **Customize configuration** - Edit `backend/config.py`

## 🆘 Still Need Help?

1. Check the full [README.md](README.md)
2. Check [backend/README.md](backend/README.md) for API details
3. Check [frontend/README.md](frontend/README.md) for frontend info
4. Review error messages carefully
5. Check Python/Java/Gradle versions

## 🎉 Success!

If you see:
- ✅ Frontend running on port 8000
- ✅ Backend running on port 3000
- ✅ Generated your first mod
- ✅ Item appears in Minecraft

**Congratulations! You're ready to create amazing mods!** 🚀

---

**Happy modding!** 🎮✨
