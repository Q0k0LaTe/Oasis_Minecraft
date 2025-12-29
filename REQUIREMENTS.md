# Minecraft Mod Generator - Project Requirements

## Project Overview
An AI-powered web application that generates custom Minecraft Fabric 1.21 mods. Users can describe an item they want to add to Minecraft, and the system will generate a complete, working mod with the custom item.

## System Architecture

### 1. Frontend (Web UI)
- **Technology Stack**: HTML/CSS/JavaScript (React/Vue/Vanilla)
- **Features**:
  - User input form for item description
  - Item customization options (name, description, properties)
  - Mod download interface
  - Preview of generated item (optional)
- **User Flow**:
  1. User enters item details (name, description, properties)
  2. User submits request to generate mod
  3. System displays generation progress
  4. User downloads compiled .jar mod file

### 2. Backend API
- **Technology Stack**: Node.js/Python/Java
- **Endpoints**:
  - `POST /api/generate-mod` - Generate mod from item description
  - `GET /api/download/:modId` - Download generated mod file
  - `GET /api/status/:jobId` - Check generation status
- **Features**:
  - Request validation
  - Job queue management
  - Mod compilation orchestration
  - File storage and serving

### 3. AI Agent
- **Purpose**: Generate Fabric 1.21 mod code
- **Input**: Item specifications (name, description, properties)
- **Output**: Complete mod source code
- **Components to Generate**:
  - Main mod class with ModInitializer
  - Item registration code
  - fabric.mod.json configuration
  - Language files (en_us.json)
  - Item model JSON
  - Item texture (default or AI-generated)
  - Gradle build configuration

### 4. Mod Compilation System
- **Technology**: Gradle wrapper
- **Process**:
  1. Receive generated source code
  2. Create temporary project directory
  3. Run `./gradlew build`
  4. Extract compiled .jar file
  5. Clean up temporary files
- **Requirements**:
  - Java 21+ runtime
  - Gradle build environment
  - Fabric development dependencies

## Minecraft Fabric 1.21 Mod Structure

### Required Files and Directories

```
mod-project/
├── gradle/
│   └── wrapper/
│       ├── gradle-wrapper.jar
│       └── gradle-wrapper.properties
├── src/
│   ├── main/
│   │   ├── java/
│   │   │   └── com/example/modid/
│   │   │       ├── ExampleMod.java (ModInitializer)
│   │   │       └── ModItems.java (Item registration)
│   │   └── resources/
│   │       ├── fabric.mod.json
│   │       └── assets/
│   │           └── modid/
│   │               ├── lang/
│   │               │   └── en_us.json
│   │               ├── models/
│   │               │   └── item/
│   │               │       └── item_name.json
│   │               ├── textures/
│   │               │   └── item/
│   │               │       └── item_name.png
│   │               └── items/
│   │                   └── item_name.json
│   └── client/
│       ├── java/
│       │   └── com/example/modid/
│       │       └── ExampleModClient.java
│       └── resources/
├── build.gradle
├── gradle.properties
└── settings.gradle
```

### Key Code Templates

#### 1. Main Mod Class (ModInitializer)
```java
public class ExampleMod implements ModInitializer {
    public static final String MOD_ID = "example-mod";

    @Override
    public void onInitialize() {
        ModItems.initialize();
    }
}
```

#### 2. Item Registration
```java
public class ModItems {
    public static final Item CUSTOM_ITEM = register(
        "item_name",
        Item::new,
        new Item.Properties()
    );

    public static Item register(String name, Function<Item.Properties, Item> factory, Item.Properties settings) {
        ResourceKey<Item> itemKey = ResourceKey.create(
            Registries.ITEM,
            ResourceLocation.fromNamespaceAndPath(ExampleMod.MOD_ID, name)
        );
        Item item = factory.apply(settings.setId(itemKey));
        Registry.register(BuiltInRegistries.ITEM, itemKey, item);
        return item;
    }

    public static void initialize() {
        ItemGroupEvents.modifyEntriesEvent(CreativeModeTabs.INGREDIENTS)
            .register((itemGroup) -> itemGroup.accept(CUSTOM_ITEM));
    }
}
```

#### 3. fabric.mod.json
```json
{
  "schemaVersion": 1,
  "id": "example-mod",
  "version": "1.0.0",
  "name": "Example Mod",
  "description": "A custom item mod",
  "authors": ["AI Generator"],
  "contact": {},
  "license": "MIT",
  "icon": "assets/example-mod/icon.png",
  "environment": "*",
  "entrypoints": {
    "main": ["com.example.modid.ExampleMod"]
  },
  "depends": {
    "fabricloader": ">=0.15.0",
    "minecraft": "~1.21",
    "java": ">=21",
    "fabric-api": "*"
  }
}
```

#### 4. Item Model JSON
```json
{
  "parent": "minecraft:item/generated",
  "textures": {
    "layer0": "example-mod:item/item_name"
  }
}
```

#### 5. Client Item Definition
```json
{
  "model": {
    "type": "minecraft:model",
    "model": "example-mod:item/item_name"
  }
}
```

## AI Agent Requirements

### Input Schema
```json
{
  "itemName": "string",
  "itemDisplayName": "string",
  "itemDescription": "string",
  "modId": "string",
  "modName": "string",
  "packageName": "string",
  "properties": {
    "maxStackSize": "number (1-64)",
    "isCompostable": "boolean",
    "compostChance": "number (0-1)",
    "isFuel": "boolean",
    "burnTime": "number (ticks)",
    "addToCreativeTab": "string (CreativeModeTabs enum)"
  }
}
```

### Output Requirements
The AI agent must generate:
1. All Java source files with proper package structure
2. All JSON configuration files
3. Default texture (16x16 PNG) or placeholder
4. Gradle build files configured for Fabric 1.21
5. Language files for item names

### Validation Rules
- Mod ID: lowercase, alphanumeric, hyphens only
- Item name: lowercase, alphanumeric, underscores only
- Package name: valid Java package naming convention
- All file paths must match naming conventions
- Code must compile without errors

## Technical Requirements

### Environment
- **Java**: Version 21 or newer
- **Gradle**: 8.0+
- **Minecraft**: 1.21.x
- **Fabric Loader**: 0.15.0+
- **Fabric API**: Latest for 1.21

### Dependencies
```gradle
dependencies {
    minecraft "com.mojang:minecraft:1.21"
    mappings "net.fabricmc:yarn:1.21+build.x:v2"
    modImplementation "net.fabricmc:fabric-loader:0.15.0"
    modImplementation "net.fabricmc.fabric-api:fabric-api:0.x.x+1.21"
}
```

## Security Considerations
- Validate all user inputs
- Sanitize mod IDs and package names
- Limit file sizes
- Implement rate limiting
- Sandbox compilation process
- Scan generated code for malicious patterns
- Timeout long-running compilations

## Future Enhancements
- Support for custom textures (AI-generated or uploaded)
- Multiple items per mod
- Item properties customization (durability, food values, etc.)
- Custom item behaviors (on-use actions)
- Block generation support
- Mob generation support
- Recipe generation
- Multi-version support (1.20.x, 1.21.x)

## Success Criteria
1. User can generate a working mod in under 30 seconds
2. Generated mods load in Minecraft 1.21 without errors
3. Items appear in creative inventory
4. Items have correct names and textures
5. Mods are properly packaged as .jar files
6. System handles at least 10 concurrent generation requests

## Development Phases

### Phase 1: MVP (Minimum Viable Product)
- Basic web form for item name and description
- AI agent generates simple item mod
- Automated compilation
- Mod file download

### Phase 2: Enhanced Features
- Item property customization
- Better UI/UX
- Progress indicators
- Error handling and user feedback

### Phase 3: Advanced Features
- Custom texture generation/upload
- Multiple items per mod
- Item groups and categories
- Recipe support

### Phase 4: Polish
- Testing suite
- Performance optimization
- Documentation
- Deployment pipeline
