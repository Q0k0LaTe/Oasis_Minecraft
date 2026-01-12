# Minecraft Mod Generator - AI-Powered Frontend

A Minecraft-styled web interface where users simply describe an item and AI generates a complete Fabric 1.21 mod.

## 🎯 Concept

**User Experience:**
1. User types a simple prompt: *"A glowing ruby gem that's rare and valuable"*
2. AI analyzes and decides everything: mod name, item properties, rarity, stack size, etc.
3. Complete mod is generated and compiled automatically
4. User downloads the .jar file

**No complex forms. No technical knowledge required. Just describe what you want.**

## ✨ Features

### 🤖 AI-Driven Generation
- **Simple prompt input** - Just describe your item in plain English
- **AI makes all decisions** - Mod name, item ID, properties, rarity, etc.
- **Smart analysis** - AI understands context (e.g., "sword" → max stack of 1, combat tab)
- **Real-time progress** - See AI analysis and generation steps

### 🎨 Minecraft-Styled UI
- **Pixelated fonts** and classic Minecraft aesthetics
- **Beveled panels** and authentic UI elements
- **Minecraft color palette** (browns, grays, greens)
- **Responsive design** - Works on desktop and mobile

### 💡 User-Friendly Features
- **Example chips** - Click to try pre-made prompts
- **Optional overrides** - Advanced users can override mod name/author
- **Progress visualization** - See each step of generation
- **AI decision preview** - Review what the AI decided before downloading
- **Keyboard shortcuts** - Ctrl/Cmd + Enter to submit

## 📁 File Structure

```
frontend/
├── index.html                 # Main page with simple prompt interface
├── QUICKSTART.md             # Quick start guide
├── README.md                 # This file
└── assets/
    ├── css/
    │   └── style.css         # Minecraft-themed styles
    ├── js/
    │   └── script.js         # AI interaction and mock logic
    └── images/               # (empty, for future assets)
```

## 🚀 How to Run

**Quick start:**
```bash
cd frontend
python3 -m http.server 8000
```

Then open: **http://localhost:8000**

## 🎮 User Flow

### 1. Enter Prompt
User types a description:
```
"A powerful emerald staff with mystical powers"
```

### 2. AI Analysis
AI decides:
- **Mod Name:** Mystical Staff Mod
- **Mod ID:** mysticalstaff
- **Item Name:** Mystical Staff
- **Item ID:** mystical_staff
- **Properties:**
  - Max Stack: 1 (because it's a staff/tool)
  - Rarity: RARE (from "mystical")
  - Fireproof: No
  - Creative Tab: TOOLS

### 3. Generation
Backend:
- Generates complete Fabric mod structure
- Creates all Java files
- Generates assets (models, textures, lang files)
- Compiles with Gradle
- Returns .jar file

### 4. Download
User gets a working Minecraft mod!

## 📝 Example Prompts

Here are prompts users can try:

| Prompt | Expected Result |
|--------|----------------|
| "A glowing blue crystal that's rare and magical" | Rare crystal item in Ingredients tab |
| "A powerful diamond sword with extra damage" | Epic sword in Combat tab, max stack 1 |
| "A golden apple that heals you when eaten" | Food item in Food & Drink tab |
| "A fireball staff that never burns" | Fireproof staff in Tools tab |
| "A rare emerald shard used for crafting" | Rare ingredient, stack of 16 |

## 🔧 Configuration

Edit the API endpoint in `assets/js/script.js`:

```javascript
const API_BASE_URL = 'http://localhost:3000/api';
```

## 📡 API Integration

The frontend sends a simple request:

### Generate Mod Endpoint
```javascript
POST /api/generate-mod
Content-Type: application/json

{
  "prompt": "A glowing ruby gem that's rare and valuable",
  "authorName": null,  // Optional
  "modName": null      // Optional override
}
```

### Expected Response
```javascript
{
  "success": true,
  "jobId": "job-abc123",
  "aiDecisions": {
    "modName": "Ruby Mod",
    "modId": "rubymod",
    "itemName": "Ruby",
    "itemId": "ruby",
    "description": "A glowing ruby gem that's rare and valuable",
    "properties": {
      "maxStackSize": 16,
      "rarity": "RARE",
      "fireproof": false,
      "creativeTab": "INGREDIENTS"
    }
  },
  "downloadUrl": "/downloads/rubymod.jar",
  "message": "Mod generated successfully!"
}
```

## 🤖 AI Decision Logic

The AI (backend) should analyze prompts and decide:

### Item Name & IDs
- Extract main item name from prompt
- Generate valid identifiers (lowercase, underscores)
- Create mod name based on item

### Rarity
- **COMMON** (white) - Default
- **UNCOMMON** (yellow) - Keywords: uncommon, special
- **RARE** (aqua) - Keywords: rare, valuable, magical
- **EPIC** (magenta) - Keywords: epic, legendary, powerful

### Max Stack Size
- **1** - Tools, weapons, staffs, armor
- **16** - Rare/epic items, special materials
- **64** - Common items, ingredients

### Fireproof
- **true** - Keywords: fireproof, fire, lava, dragon, nether
- **false** - Default

### Creative Tab
- **COMBAT** - Swords, weapons
- **TOOLS** - Tools, staffs, utilities
- **FOOD_AND_DRINK** - Food, potions, edibles
- **INGREDIENTS** - Materials, gems, resources (default)
- **BUILDING_BLOCKS** - Blocks, construction materials
- **FUNCTIONAL** - Functional items

## 🎨 Customization

### Colors
Edit CSS variables in `assets/css/style.css`:

```css
:root {
    --mc-aqua: #55ffff;     /* Rare items */
    --mc-magenta: #ff55ff;  /* Epic items */
    --mc-yellow: #ffff55;   /* Uncommon items */
    --mc-green: #55ff55;    /* Success messages */
    --mc-red: #ff5555;      /* Error messages */
}
```

### Mock API Behavior
To test different AI decisions, edit `mockAIDecisions()` in `script.js`.

## 🌐 Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers

## ✅ Current Features

- ✅ Simple prompt textarea
- ✅ Example chips for quick testing
- ✅ Optional advanced options (author, mod name override)
- ✅ Mock AI decision logic
- ✅ Loading overlay with progress steps
- ✅ AI analysis preview panel
- ✅ Success/error handling
- ✅ Mod details display
- ✅ Download button
- ✅ Responsive design
- ✅ Keyboard shortcuts

## 🔄 Next Steps

To make this production-ready:

1. **Backend Integration**
   - Replace mock API with real backend
   - Integrate with actual AI (GPT-4, Claude, etc.)
   - Set up mod generation pipeline

2. **AI Improvements**
   - Better prompt parsing
   - More sophisticated property detection
   - Support for custom textures from AI image generation

3. **Features**
   - Item preview rendering
   - Multiple items per mod
   - Advanced properties (durability, food values, enchantments)
   - User accounts and history
   - Shareable mod links

## 📖 User Documentation

### For Users

**How to create a mod:**

1. Describe your item in the text box (be as detailed or simple as you want)
2. Click "Generate Mod" or press Ctrl+Enter
3. Wait while AI analyzes and generates your mod (~10-30 seconds)
4. Review the AI's decisions
5. Download your .jar file
6. Place it in your Minecraft `mods` folder
7. Launch Minecraft with Fabric 1.21

**Tips for better results:**
- Include item type (sword, gem, staff, apple, etc.)
- Mention desired rarity (rare, epic, common)
- Specify special properties (fireproof, glowing, magical)
- Describe what it does or looks like

**Good prompts:**
- ✅ "A rare ruby gem used for crafting powerful items"
- ✅ "An enchanted diamond sword that glows in the dark"
- ✅ "A golden apple that restores health and grants regeneration"
- ✅ "A mystical staff that shoots fireballs and never burns"

**Less effective prompts:**
- ❌ "item" (too vague)
- ❌ "something cool" (AI can't infer specifics)
- ❌ "test" (no context)

## 🐛 Troubleshooting

**Mod doesn't load in Minecraft:**
- Ensure you have Fabric Loader 0.15.11+ installed
- Verify Minecraft version is 1.21
- Check Fabric API is installed
- Look at Minecraft logs for errors

**Generation fails:**
- Check your internet connection
- Ensure prompt is at least 5 characters
- Try a simpler prompt
- Check browser console for errors

## 📄 License

Part of the Minecraft Mod Generator project.

---

**Made with ❤️ for the Minecraft modding community**
