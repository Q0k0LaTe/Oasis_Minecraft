# Quick Start Guide - AI-Powered Minecraft Mod Generator

## 🚀 Running the Frontend

### Method 1: Python (Easiest)

```bash
cd frontend
python3 -m http.server 8000
```

Open your browser to: **http://localhost:8000**

### Method 2: Node.js

```bash
cd frontend
npx http-server -p 8000
```

Open your browser to: **http://localhost:8000**

### Method 3: PHP

```bash
cd frontend
php -S localhost:8000
```

Open your browser to: **http://localhost:8000**

## 🎮 How It Works

### The AI-Powered Experience

Unlike traditional mod generators that require you to fill out complex forms, this is **dead simple**:

1. **Type a description** of your item (a few words or sentences)
2. **Click "Generate Mod"** (or press Ctrl+Enter)
3. **Wait ~10-30 seconds** while AI does everything
4. **Download your .jar file**

That's it! No technical knowledge required.

## 💡 Try These Examples

Click any of the example chips on the page, or type these prompts:

### Simple Examples
```
A ruby gem
```
```
A magic sword
```
```
A golden apple
```

### Detailed Examples
```
A glowing blue crystal that's rare and magical
```
```
A powerful diamond sword with extra damage
```
```
A golden apple that heals you when eaten
```
```
A fireball staff that never burns in lava
```
```
An ancient tome filled with mystical knowledge
```

## 🤖 What the AI Decides

The AI automatically figures out:

✅ **Mod Name** - e.g., "Ruby Mod", "Magic Sword Mod"
✅ **Mod ID** - e.g., "rubymod", "magicsword"
✅ **Item Name** - e.g., "Ruby", "Magic Sword"
✅ **Item ID** - e.g., "ruby", "magic_sword"
✅ **Rarity** - Common, Uncommon, Rare, or Epic
✅ **Max Stack Size** - 1 for tools/weapons, 16 for rare items, 64 for common
✅ **Fireproof** - Based on context (fire, lava, dragon, etc.)
✅ **Creative Tab** - Combat, Tools, Food, Ingredients, etc.

## 🎯 What You'll See

### 1. Loading Screen
Watch the AI work through these steps:
- ○ Analyzing your prompt...
- ○ AI is deciding item properties...
- ○ Generating mod structure...
- ○ Creating Java files...
- ○ Generating assets...
- ○ Compiling mod...

### 2. AI Analysis Panel
See what the AI decided:
```
🎯 AI Generated Mod Name: Ruby Mod
✨ Item Name: Ruby

┌─────────────┬──────────────┬────────────┐
│ Mod ID      │ Item ID      │ Max Stack  │
│ rubymod     │ ruby         │ 16         │
├─────────────┼──────────────┼────────────┤
│ Rarity      │ Fireproof    │ Creative   │
│ RARE        │ No           │ Ingredients│
└─────────────┴──────────────┴────────────┘
```

### 3. Download Panel
Your mod is ready!
- Download button for the .jar file
- Complete mod details
- Option to create another mod

## ⚙️ Advanced Options (Optional)

Click **"Advanced Options"** to override:
- **Your Name** - Custom author name (default: "AI Generator")
- **Mod Name** - Override the AI-generated mod name

## 🎨 Current State: Mock Mode

**Note:** The frontend currently uses **mock AI logic** for demonstration:

- Generation takes ~5 seconds (simulated)
- Uses simple keyword matching for decisions
- No actual mod compilation yet
- Download button is a placeholder

**When backend is ready:**
- Real AI analysis using GPT-4/Claude
- Actual Fabric mod generation
- Gradle compilation
- Working .jar download

## 🔧 Testing Tips

### Try Different Prompts

**Weapons:**
```
A legendary diamond sword
A fire staff that shoots fireballs
An enchanted bow with infinite arrows
```

**Gems/Materials:**
```
A rare sapphire gem
An epic emerald shard
A common copper ingot
```

**Food:**
```
A magical golden apple
A healing potion in a bottle
Enchanted bread that never spoils
```

**Special Items:**
```
A dragon scale that's fireproof
A mystical orb that glows in the dark
An ancient artifact with legendary power
```

### Watch AI Decisions

Notice how the AI:
- Gives swords **max stack of 1** and **Combat tab**
- Makes "rare" items **RARE rarity** with **stack of 16**
- Puts food items in **Food & Drink tab**
- Makes items with "fire" or "dragon" **fireproof**
- Chooses appropriate **creative tabs** based on item type

## 🎯 Next Steps

1. **Try the mock interface** - Get a feel for the UX
2. **Test different prompts** - See what the AI decides
3. **Build the backend** - Connect to real AI and mod generation
4. **Replace mock API** - Uncomment real API calls in `script.js`
5. **Deploy** - Make it available to users!

## 💡 Tips for Users

**Be descriptive but not complex:**
- ✅ "A rare ruby used for crafting"
- ✅ "A sword that deals fire damage"
- ❌ "Create a mod with a ruby that has specific NBT data..." (too technical)

**Keywords that help AI:**
- **Rarity**: rare, epic, legendary, uncommon, common
- **Type**: sword, gem, staff, apple, potion, tool
- **Properties**: fireproof, glowing, magical, enchanted
- **Use**: crafting, fighting, eating, building

**The AI understands context:**
- "sword" → Combat tab, max stack 1
- "gem" → Ingredients tab, various stack sizes
- "food" → Food & Drink tab
- "fireproof" → Fireproof property enabled

## 📱 Mobile Support

The interface is fully responsive! Works great on:
- 📱 Mobile phones
- 📱 Tablets
- 💻 Desktop
- 🖥️ Large monitors

## ⌨️ Keyboard Shortcuts

- **Ctrl+Enter** (or Cmd+Enter on Mac) - Submit form
- **Tab** - Navigate between fields
- **Esc** - (future) Close panels

## 🐛 Troubleshooting

**Can't see the page?**
- Check the URL: `http://localhost:8000`
- Make sure the server is running
- Try a different port if 8000 is busy

**Example chips not working?**
- JavaScript should be enabled
- Check browser console for errors
- Try refreshing the page

**Looks broken?**
- Hard refresh: Ctrl+Shift+R (or Cmd+Shift+R on Mac)
- Clear browser cache
- Check if CSS loaded correctly

## 🎉 Have Fun!

Experiment with different prompts and see what the AI creates. The simpler you keep your descriptions, the better the results!

---

**Ready to build real mods?** Connect the backend and let's make some magic! ✨
