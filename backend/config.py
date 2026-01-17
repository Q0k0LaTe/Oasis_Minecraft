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
AI_REQUEST_TIMEOUT = float(os.getenv("AI_REQUEST_TIMEOUT", "120.0"))  # Timeout in seconds for AI requests
AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "3"))  # Max retries for failed requests

# Image Generation - Using Gemini 3 Pro Image Preview
IMAGE_MODEL = "gemini-3-pro-image-preview"  # Gemini 3 Pro for texture generation with reference guidance
IMAGE_SIZE = "1024x1024"  # Will be resized to 16x16
IMAGE_QUALITY = "standard"  # standard or hd
IMAGE_VARIANT_COUNT = 5  # Number of texture variants to generate for user selection
IMAGE_GENERATION_TIMEOUT = float(os.getenv("IMAGE_GENERATION_TIMEOUT", "180.0"))  # Longer timeout for image generation

# =============================================================================
# Environment Detection (used by multiple config sections)
# =============================================================================
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"

# Server Configuration
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "3000"))

# CORS Configuration
# In production, set CORS_ALLOWED_ORIGINS environment variable with comma-separated trusted domains
# Example: CORS_ALLOWED_ORIGINS=https://example.com,https://app.example.com
_cors_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
if _cors_env:
    # Production: use explicitly configured origins only
    CORS_ORIGINS = [origin.strip() for origin in _cors_env.split(",") if origin.strip()]
else:
    # Development: allow common localhost origins (no wildcard!)
    CORS_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:5173",
    ]

# Validate CORS configuration in production
if IS_PRODUCTION and not _cors_env:
    import warnings
    warnings.warn(
        "⚠️  CORS_ALLOWED_ORIGINS not set in production! "
        "Using localhost defaults which may not work. "
        "Set CORS_ALLOWED_ORIGINS environment variable.",
        RuntimeWarning
    )

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "minecraft_mod_generator")

# Database credentials: REQUIRED in production, optional defaults in development
_db_user_env = os.getenv("DB_USER")
_db_password_env = os.getenv("DB_PASSWORD")

if IS_PRODUCTION:
    # Production: credentials are mandatory, no defaults allowed
    if not _db_user_env:
        raise ValueError(
            "DB_USER environment variable is required in production. "
            "Set ENVIRONMENT=development to use defaults for local development."
        )
    if not _db_password_env:
        raise ValueError(
            "DB_PASSWORD environment variable is required in production. "
            "Set ENVIRONMENT=development to use defaults for local development."
        )
    DB_USER = _db_user_env
    DB_PASSWORD = _db_password_env
else:
    # Development: allow defaults for convenience (with warning if using defaults)
    DB_USER = _db_user_env or "oasis"
    DB_PASSWORD = _db_password_env or "oasis123"
    if not _db_user_env or not _db_password_env:
        import warnings
        warnings.warn(
            "⚠️  Using default database credentials (DB_USER/DB_PASSWORD). "
            "This is only acceptable for local development. "
            "Set these environment variables for production use.",
            RuntimeWarning
        )

# Construct database URL for SQLAlchemy
# Format: postgresql://user:password@host:port/database
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Redis Configuration (for verification codes and rate limiting)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# =============================================================================
# IP Rate Limiting Configuration
# =============================================================================
# Global rate limit: max requests per IP in a 10-second window
RATE_LIMIT_GLOBAL_MAX = int(os.getenv("RATE_LIMIT_GLOBAL_MAX", "30"))
RATE_LIMIT_GLOBAL_WINDOW = int(os.getenv("RATE_LIMIT_GLOBAL_WINDOW", "10"))

# Burst rate limit: max requests per IP in a 1-second window
RATE_LIMIT_BURST_MAX = int(os.getenv("RATE_LIMIT_BURST_MAX", "10"))
RATE_LIMIT_BURST_WINDOW = int(os.getenv("RATE_LIMIT_BURST_WINDOW", "1"))

# High-risk endpoint rate limits (stricter)
# Auth endpoints: login, register, verification
RATE_LIMIT_AUTH_MAX = int(os.getenv("RATE_LIMIT_AUTH_MAX", "10"))
RATE_LIMIT_AUTH_WINDOW = int(os.getenv("RATE_LIMIT_AUTH_WINDOW", "60"))

# Send verification code: very strict to prevent email abuse
RATE_LIMIT_VERIFICATION_MAX = int(os.getenv("RATE_LIMIT_VERIFICATION_MAX", "3"))
RATE_LIMIT_VERIFICATION_WINDOW = int(os.getenv("RATE_LIMIT_VERIFICATION_WINDOW", "60"))

# Resource-intensive endpoints: build, AI generation
RATE_LIMIT_RESOURCE_MAX = int(os.getenv("RATE_LIMIT_RESOURCE_MAX", "5"))
RATE_LIMIT_RESOURCE_WINDOW = int(os.getenv("RATE_LIMIT_RESOURCE_WINDOW", "60"))

# Paths to exclude from rate limiting (comma-separated)
# Default: docs, health check, static files
RATE_LIMIT_EXCLUDE_PATHS = [
    p.strip() for p in os.getenv(
        "RATE_LIMIT_EXCLUDE_PATHS",
        "/docs,/redoc,/openapi.json,/api/health,/"
    ).split(",") if p.strip()
]

# Whitelist IPs (comma-separated, supports CIDR notation)
# Default: localhost only
RATE_LIMIT_WHITELIST_IPS = [
    ip.strip() for ip in os.getenv(
        "RATE_LIMIT_WHITELIST_IPS",
        "127.0.0.1,::1"
    ).split(",") if ip.strip()
]

# Fail behavior when Redis is unavailable
# Options: "closed" (deny, more secure), "open" (allow, more available)
# Default: "closed" for production, "open" for development
RATE_LIMIT_FAIL_MODE = os.getenv(
    "RATE_LIMIT_FAIL_MODE",
    "closed" if IS_PRODUCTION else "open"
)

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

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
# Note: GOOGLE_CLIENT_SECRET is not required for ID token verification
# We only need CLIENT_ID to verify tokens from Google

# Admin Configuration
# Comma-separated list of admin email addresses
ADMIN_EMAILS = [email.strip().lower() for email in os.getenv("ADMIN_EMAILS", "").split(",") if email.strip()]

# =============================================================================
# Session & Cookie Configuration
# =============================================================================
# Session duration in seconds (default: 7 days)
SESSION_EXPIRE_DAYS = int(os.getenv("SESSION_EXPIRE_DAYS", "7"))
SESSION_EXPIRE_SECONDS = SESSION_EXPIRE_DAYS * 24 * 60 * 60

# Cookie settings
SESSION_COOKIE_NAME = "session_token"
SESSION_COOKIE_MAX_AGE = SESSION_EXPIRE_SECONDS  # Same as session expiry

# Security settings - adjust for production
# In development: Secure=False allows HTTP, SameSite=Lax for convenience
# In production: Secure=True requires HTTPS, SameSite=Strict for max security
SESSION_COOKIE_SECURE = IS_PRODUCTION  # True in production (HTTPS only)
SESSION_COOKIE_SAMESITE = "strict" if IS_PRODUCTION else "lax"  # CSRF protection
SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN", None)  # None = same domain only
