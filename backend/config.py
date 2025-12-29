"""
Configuration for the Minecraft Mod Generator Backend
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

# Paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
GENERATED_DIR = BASE_DIR / "generated"
DOWNLOADS_DIR = BASE_DIR / "downloads"

# Create directories if they don't exist
GENERATED_DIR.mkdir(exist_ok=True)
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Minecraft/Fabric Configuration (override via environment variables to match your client)
DEFAULT_MC_VERSION = "1.21.5"
FABRIC_API_DEFAULTS = {
    "1.21": "0.102.0+1.21",
    "1.21.1": "0.105.0+1.21.1",
    "1.21.5": "0.128.2+1.21.5",
}

MINECRAFT_VERSION = os.getenv("MINECRAFT_VERSION", DEFAULT_MC_VERSION)
FABRIC_LOADER_VERSION = os.getenv("FABRIC_LOADER_VERSION", "0.16.13")
FABRIC_API_VERSION = os.getenv("FABRIC_API_VERSION")
if not FABRIC_API_VERSION:
    FABRIC_API_VERSION = FABRIC_API_DEFAULTS.get(MINECRAFT_VERSION)

if not FABRIC_API_VERSION:
    fallback_version = FABRIC_API_DEFAULTS[DEFAULT_MC_VERSION]
    print(
        f"[Config] Warning: no Fabric API version mapped for Minecraft {MINECRAFT_VERSION}. "
        f"Defaulting to {fallback_version}. Set FABRIC_API_VERSION to override."
    )
    FABRIC_API_VERSION = fallback_version

DEFAULT_YARN_BUILD = "build.1" if MINECRAFT_VERSION == "1.21.5" else "build.2"
YARN_MAPPINGS = os.getenv("YARN_MAPPINGS", f"{MINECRAFT_VERSION}+{DEFAULT_YARN_BUILD}")
JAVA_VERSION = os.getenv("JAVA_VERSION", "21")

# Resource Pack Configuration
RESOURCE_PACK_FORMAT = int(os.getenv("RESOURCE_PACK_FORMAT", "34"))

# AI Configuration - Using Gemini
AI_MODEL = "gemini-2.0-flash-exp"  # Gemini model for text generation
AI_TEMPERATURE = 0.7

# Image Generation - Using Google Imagen (via Gemini)
IMAGE_MODEL = "imagen-3.0-generate-001"  # Google Imagen for generating item textures
IMAGE_SIZE = "1024x1024"  # Will be resized to 16x16
IMAGE_QUALITY = "standard"  # standard or hd

# Server Configuration
HOST = "0.0.0.0"
PORT = 3000
CORS_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "*"  # Allow all origins during development
]
