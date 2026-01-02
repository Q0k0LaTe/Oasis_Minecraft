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
    "1.21.11": "0.140.2+1.21.11"
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

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "minecraft_mod_generator")
DB_USER = os.getenv("DB_USER", "oasis")
DB_PASSWORD = os.getenv("DB_PASSWORD", "oasis123")

# Construct database URL for SQLAlchemy
# Format: postgresql://user:password@host:port/database
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Redis Configuration (for verification codes)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Email Configuration (Resend)
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
if not RESEND_API_KEY:
    raise ValueError("RESEND_API_KEY not found in environment variables")

# Resend 配置
MAIL_FROM = os.getenv("MAIL_FROM", "onboarding@resend.dev")  # Resend 默认发件地址
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "Minecraft Mod Generator")

# 旧的 Gmail SMTP 配置（已弃用，保留作为备份）
# MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
# MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
# MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
# MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
# MAIL_STARTTLS = True
# MAIL_SSL_TLS = False
# MAIL_USE_CREDENTIALS = True

# Verification Code Configuration
VERIFICATION_CODE_EXPIRE_MINUTES = int(os.getenv("VERIFICATION_CODE_EXPIRE_MINUTES", "10"))  # Code expires in 10 minutes
VERIFICATION_CODE_LENGTH = int(os.getenv("VERIFICATION_CODE_LENGTH", "6"))  # 6-digit code
