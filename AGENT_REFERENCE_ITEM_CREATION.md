# AI Agent Reference: Fabric 1.21 Item Creation Guide

## Overview
This document serves as a reference for the AI agent to generate Minecraft Fabric 1.21 mods that add custom items. Based on analysis of the [retutorial-template-1.21-pre2](https://github.com/BeiShanair/retutorial-template-1.21-pre2) repository.

---

## Project Configuration

### Minecraft & Fabric Versions (gradle.properties)
```properties
# Minecraft and Fabric versions
minecraft_version=1.21-pre2
yarn_mappings=1.21-pre2+build.2
loader_version=0.15.11

# Mod Properties
mod_version=0.1-1.21-pre2
maven_group=com.example.modid
archives_base_name=modname

# Fabric API
fabric_version=0.99.4+1.21

# Build Configuration
org.gradle.jvmargs=-Xmx1G
org.gradle.parallel=true
```

### Build Configuration (build.gradle)
```gradle
plugins {
    id 'fabric-loom' version '1.6-SNAPSHOT'
    id 'maven-publish'
}

version = project.mod_version
group = project.maven_group

repositories {
    // Add repositories to retrieve artifacts from in here.
    // You should only use this when depending on other mods because
    // Loom adds the essential maven repositories to download Minecraft and libraries from automatically.
}

dependencies {
    // Minecraft and Fabric
    minecraft "com.mojang:minecraft:${project.minecraft_version}"
    mappings "net.fabricmc:yarn:${project.yarn_mappings}:v2"
    modImplementation "net.fabricmc:fabric-loader:${project.loader_version}"

    // Fabric API
    modImplementation "net.fabricmc.fabric-api:fabric-api:${project.fabric_version}"
}

java {
    sourceCompatibility = JavaVersion.VERSION_21
    targetCompatibility = JavaVersion.VERSION_21

    withSourcesJar()
}

tasks.withType(JavaCompile).configureEach {
    it.options.release = 21
}

processResources {
    inputs.property "version", project.version

    filesMatching("fabric.mod.json") {
        expand "version": project.version
    }
}

jar {
    from("LICENSE") {
        rename { "${it}_${project.archives_base_name}"}
    }
}
```

### Mod Metadata (fabric.mod.json)
```json
{
    "schemaVersion": 1,
    "id": "modid",
    "version": "${version}",
    "name": "Mod Name",
    "description": "Mod description here",
    "authors": [
        "Author Name"
    ],
    "contact": {
        "homepage": "https://fabricmc.net/",
        "sources": "https://github.com/username/modname"
    },
    "license": "CC0-1.0",
    "icon": "assets/modid/icon.png",
    "environment": "*",
    "entrypoints": {
        "main": [
            "com.example.modid.ModName"
        ],
        "fabric-datagen": [
            "com.example.modid.ModNameDataGenerator"
        ],
        "client": [
            "com.example.modid.ModNameClient"
        ]
    },
    "mixins": [
        "modid.mixins.json"
    ],
    "depends": {
        "fabricloader": ">=0.15.11",
        "minecraft": "~1.21-",
        "java": ">=21",
        "fabric-api": "*"
    }
}
```

---

## Code Structure

### 1. Main Mod Class (ModInitializer)

**Path:** `src/main/java/com/example/modid/ModName.java`

```java
package com.example.modid;

import net.fabricmc.api.ModInitializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class ModName implements ModInitializer {
    public static final String MOD_ID = "modid";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    @Override
    public void onInitialize() {
        // This code runs as soon as Minecraft is in a mod-load-ready state.
        // However, some things (like resources) may still be uninitialized.
        // Proceed with mild caution.

        ModItems.registerModItems();

        LOGGER.info("Hello Fabric world from {}!", MOD_ID);
    }
}
```

**Key Points:**
- Implements `ModInitializer` interface
- Defines `MOD_ID` constant used throughout the mod
- Creates a logger for debugging
- Calls item registration in `onInitialize()`

---

### 2. Item Registration Class

**Path:** `src/main/java/com/example/modid/item/ModItems.java`

```java
package com.example.modid.item;

import com.example.modid.ModName;
import net.minecraft.item.Item;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.util.Identifier;

public class ModItems {

    // ==================== ITEM DECLARATIONS ====================

    /**
     * Example: Simple item with default settings
     */
    public static final Item CUSTOM_ITEM = registerItems("custom_item",
        new Item(new Item.Settings()));

    /**
     * Example: Item with max stack size of 16
     */
    public static final Item RARE_ITEM = registerItems("rare_item",
        new Item(new Item.Settings().maxCount(16)));

    /**
     * Example: Fireproof item
     */
    public static final Item FIRE_RESISTANT_ITEM = registerItems("fire_resistant_item",
        new Item(new Item.Settings().fireproof()));


    // ==================== REGISTRATION METHOD ====================

    /**
     * Registers an item with the game's item registry
     * @param name The item's registry name (lowercase, underscores)
     * @param item The Item instance to register
     * @return The registered item
     */
    private static Item registerItems(String name, Item item) {
        ModName.LOGGER.info("Registering Item: {}", name);
        return Registry.register(Registries.ITEM,
            Identifier.of(ModName.MOD_ID, name), item);
    }


    // ==================== INITIALIZATION ====================

    /**
     * Called from the main mod class to trigger static initialization
     * This ensures all items are registered during mod loading
     */
    public static void registerModItems() {
        ModName.LOGGER.info("Registering items for {}", ModName.MOD_ID);
        // Static fields are initialized when class is loaded
        // This method serves to trigger that initialization at the right time
    }
}
```

**Pattern Explanation:**

1. **Static Final Fields**: Each item is declared as `public static final`
   - This makes them accessible from anywhere: `ModItems.CUSTOM_ITEM`
   - The `final` ensures they can't be reassigned

2. **Registration Helper**: The `registerItems()` method:
   - Takes the item's name and the Item instance
   - Creates an Identifier combining `MOD_ID` and the item name
   - Registers it to `Registries.ITEM`
   - Logs the registration for debugging
   - Returns the registered item

3. **Item.Settings()**: Configures item properties:
   - `.maxCount(int)` - Maximum stack size (default: 64)
   - `.fireproof()` - Item won't burn in fire/lava
   - `.maxDamage(int)` - Makes item damageable (tools/armor)
   - `.food(FoodComponent)` - Makes item edible
   - `.rarity(Rarity)` - Changes item name color

4. **Initialization Method**: `registerModItems()` is called from the main mod class
   - Triggers static field initialization
   - Ensures items are registered at the correct time in mod loading

---

### 3. Client-Side Initialization (Optional)

**Path:** `src/main/java/com/example/modid/ModNameClient.java`

```java
package com.example.modid;

import net.fabricmc.api.ClientModInitializer;

public class ModNameClient implements ClientModInitializer {
    @Override
    public void onInitializeClient() {
        // Client-specific initialization
        // Add item to creative inventory, register renderers, etc.
    }
}
```

---

### 4. Data Generator (Optional but Recommended)

**Path:** `src/main/java/com/example/modid/ModNameDataGenerator.java`

```java
package com.example.modid;

import net.fabricmc.fabric.api.datagen.v1.DataGeneratorEntrypoint;
import net.fabricmc.fabric.api.datagen.v1.FabricDataGenerator;

public class ModNameDataGenerator implements DataGeneratorEntrypoint {
    @Override
    public void onInitializeDataGenerator(FabricDataGenerator fabricDataGenerator) {
        // Register data providers here:
        // - Model providers
        // - Language providers
        // - Recipe providers
        // - Loot table providers
        // etc.
    }
}
```

---

## Asset Files

### Directory Structure
```
src/main/resources/
└── assets/
    └── modid/
        ├── icon.png (mod icon, 512x512 recommended)
        ├── lang/
        │   └── en_us.json (English translations)
        ├── models/
        │   └── item/
        │       └── custom_item.json (item model)
        └── textures/
            └── item/
                └── custom_item.png (item texture, 16x16)
```

### Language File (en_us.json)

**Path:** `src/main/resources/assets/modid/lang/en_us.json`

```json
{
    "item.modid.custom_item": "Custom Item",
    "item.modid.rare_item": "Rare Item",
    "item.modid.fire_resistant_item": "Fire Resistant Item"
}
```

**Naming Convention:** `item.<modid>.<item_name>`

---

### Item Model

**Path:** `src/main/resources/assets/modid/models/item/custom_item.json`

```json
{
    "parent": "minecraft:item/generated",
    "textures": {
        "layer0": "modid:item/custom_item"
    }
}
```

**For Handheld Items (swords, tools):**
```json
{
    "parent": "minecraft:item/handheld",
    "textures": {
        "layer0": "modid:item/custom_item"
    }
}
```

**Multi-Layer Textures:**
```json
{
    "parent": "minecraft:item/generated",
    "textures": {
        "layer0": "modid:item/custom_item_base",
        "layer1": "modid:item/custom_item_overlay"
    }
}
```

---

### Item Texture

**Path:** `src/main/resources/assets/modid/textures/item/custom_item.png`

**Requirements:**
- **Size**: 16x16 pixels (can be larger if using resource packs with higher resolution)
- **Format**: PNG with transparency support
- **Color Space**: RGB/RGBA
- **Naming**: Must match the item's registry name (e.g., `custom_item.png` for `custom_item`)

---

## Common Item Settings

### Basic Properties

```java
// Default item (stack size 64)
new Item(new Item.Settings())

// Custom stack size
new Item(new Item.Settings().maxCount(16))

// Non-stackable (like tools)
new Item(new Item.Settings().maxCount(1))

// Fireproof (won't burn in lava)
new Item(new Item.Settings().fireproof())

// Rarity (affects name color)
new Item(new Item.Settings().rarity(Rarity.RARE))  // Aqua
new Item(new Item.Settings().rarity(Rarity.EPIC))  // Magenta
```

### Damageable Items (Tools/Armor)

```java
// Item with durability
new Item(new Item.Settings().maxDamage(250))

// Using tool material
new SwordItem(ToolMaterials.IRON, 3, -2.4F, new Item.Settings())
```

### Food Items

```java
// Simple food item
new Item(new Item.Settings().food(
    new FoodComponent.Builder()
        .hunger(4)              // Hunger points restored
        .saturationModifier(0.3f) // Saturation modifier
        .build()
))

// Food with status effects
new Item(new Item.Settings().food(
    new FoodComponent.Builder()
        .hunger(4)
        .saturationModifier(0.5f)
        .statusEffect(new StatusEffectInstance(StatusEffects.REGENERATION, 100, 0), 1.0f)
        .alwaysEdible()         // Can eat even when full
        .build()
))
```

### Creative Tab Assignment

Add items to creative inventory tabs:

```java
// In your client initializer or main class
ItemGroupEvents.modifyEntriesEvent(ItemGroups.INGREDIENTS)
    .register(entries -> {
        entries.add(ModItems.CUSTOM_ITEM);
        entries.add(ModItems.RARE_ITEM);
    });

// Other available groups:
// ItemGroups.BUILDING_BLOCKS
// ItemGroups.COLORED_BLOCKS
// ItemGroups.NATURAL
// ItemGroups.FUNCTIONAL
// ItemGroups.REDSTONE
// ItemGroups.TOOLS
// ItemGroups.COMBAT
// ItemGroups.FOOD_AND_DRINK
// ItemGroups.INGREDIENTS
// ItemGroups.SPAWN_EGGS
```

---

## Complete Example: Creating a Ruby Item

### 1. Add to ModItems.java

```java
public static final Item RUBY = registerItems("ruby",
    new Item(new Item.Settings()
        .rarity(Rarity.RARE)
        .fireproof()
    ));
```

### 2. Language File (en_us.json)

```json
{
    "item.modid.ruby": "Ruby"
}
```

### 3. Item Model (models/item/ruby.json)

```json
{
    "parent": "minecraft:item/generated",
    "textures": {
        "layer0": "modid:item/ruby"
    }
}
```

### 4. Texture File

Create `textures/item/ruby.png` - a 16x16 PNG image of a ruby

### 5. Add to Creative Tab (Optional)

```java
ItemGroupEvents.modifyEntriesEvent(ItemGroups.INGREDIENTS)
    .register(entries -> entries.add(ModItems.RUBY));
```

---

## AI Agent Generation Checklist

When generating a Fabric 1.21 mod with a custom item, ensure:

### Code Generation
- [ ] Main mod class implementing `ModInitializer`
- [ ] `MOD_ID` constant defined
- [ ] Item registration class with proper package
- [ ] Items declared as `public static final`
- [ ] Registration method using `Registry.register()`
- [ ] `registerModItems()` called in main mod's `onInitialize()`
- [ ] Proper import statements

### Configuration Files
- [ ] `fabric.mod.json` with correct mod ID, name, version
- [ ] Entrypoints properly defined
- [ ] Dependencies specified (Fabric Loader, Minecraft, Java 21, Fabric API)
- [ ] `build.gradle` with correct versions
- [ ] `gradle.properties` with version numbers
- [ ] `settings.gradle` with project name

### Asset Files
- [ ] Language file (`lang/en_us.json`) with item translation
- [ ] Item model JSON (`models/item/<name>.json`)
- [ ] Item texture PNG (`textures/item/<name>.png`) or placeholder
- [ ] Mod icon (`icon.png`)

### Naming Conventions
- [ ] Mod ID: lowercase, alphanumeric, hyphens/underscores only
- [ ] Item names: lowercase, underscores for spaces
- [ ] Package names: valid Java convention (lowercase, dots)
- [ ] Class names: PascalCase
- [ ] File paths match registry names

### Build System
- [ ] Gradle wrapper files included
- [ ] Java 21 compatibility set
- [ ] Fabric Loom plugin configured
- [ ] Dependencies correctly specified

---

## Common Pitfalls to Avoid

1. **Incorrect Identifier Format**: Always use `Identifier.of(modId, name)` not `new Identifier()`
2. **Missing Static Initialization**: Must call `registerModItems()` from main mod class
3. **Typos in Paths**: Asset paths must exactly match registry names
4. **Wrong Java Version**: Must use Java 21 for Minecraft 1.21
5. **Case Sensitivity**: Registry names should be lowercase
6. **Missing Dependencies**: Always include Fabric API
7. **Incorrect Package Structure**: Package must match mod ID and organization

---

## File Path Reference

### Java Source Files
```
src/main/java/
└── com/example/modid/
    ├── ModName.java              (Main mod class)
    ├── ModNameClient.java        (Client entrypoint)
    ├── ModNameDataGenerator.java (Data generation)
    └── item/
        └── ModItems.java         (Item registration)
```

### Resource Files
```
src/main/resources/
├── fabric.mod.json               (Mod metadata)
├── modid.mixins.json            (Mixin configuration)
└── assets/modid/
    ├── icon.png                  (Mod icon)
    ├── lang/
    │   └── en_us.json           (English translations)
    ├── models/
    │   └── item/
    │       └── <itemname>.json  (Item model)
    └── textures/
        └── item/
            └── <itemname>.png   (Item texture)
```

### Build Files
```
.
├── build.gradle                  (Build configuration)
├── gradle.properties            (Version properties)
├── settings.gradle              (Project settings)
└── gradle/
    └── wrapper/
        ├── gradle-wrapper.jar
        └── gradle-wrapper.properties
```

---

## Version Information Summary

| Component | Version |
|-----------|---------|
| Minecraft | 1.21-pre2 |
| Fabric Loader | 0.15.11 |
| Fabric API | 0.99.4+1.21 |
| Yarn Mappings | 1.21-pre2+build.2 |
| Java | 21 |
| Gradle | 8.x (via Loom 1.6) |

---

## Reference Repository

This guide is based on: [BeiShanair/retutorial-template-1.21-pre2](https://github.com/BeiShanair/retutorial-template-1.21-pre2)

**Template Pattern Used:**
- Simple, clean item registration
- Logging for debugging
- Separation of concerns (items in separate class)
- Ready for data generation
- Minimal boilerplate

---

## Additional Resources

- [Official Fabric Documentation](https://docs.fabricmc.net/)
- [Fabric Wiki](https://fabricmc.net/wiki/)
- [Fabric API JavaDocs](https://maven.fabricmc.net/docs/fabric-api-0.99.4+1.21/)
- [Minecraft Wiki](https://minecraft.wiki/)
