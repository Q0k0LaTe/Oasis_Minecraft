"""
FastAPI Backend for Minecraft Mod Generator - IDE Edition

New architecture (v2):
- Workspace: Minecraft Mod projects (like IDE workspaces)
- Conversation: Chat threads within workspaces
- Message: User/assistant messages
- Run: Long-running generation/build tasks
- Asset: Textures, covers, and other resources

API Structure:
- /api/auth/* - Authentication (preserved from v1)
- /api/workspaces/* - Workspace CRUD + spec management
- /api/conversations/* - Conversation management
- /api/runs/* - Run management + SSE events
- /api/assets/* - Asset upload/management

Security:
- IP-based rate limiting (global + burst + path-specific)
- CORS protection
- Session-based authentication
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import HOST, PORT, CORS_ORIGINS
from routers import auth, workspaces, conversations, runs, assets, subscriptions
from utils.ip_rate_limit_middleware import IPRateLimitMiddleware

# Initialize FastAPI app
app = FastAPI(
    title="Minecraft Mod Generator API",
    description="AI-powered Minecraft Fabric mod generator - IDE Edition",
    version="2.0.0"
)

# Add middlewares (order matters - first added = outermost = processed first)
# 1. CORS middleware (outermost - handles CORS headers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. IP Rate Limiting middleware (after CORS, before routing)
# This protects all endpoints with:
# - Global limit: 30 requests per 10 seconds per IP
# - Burst limit: 10 requests per 1 second per IP
# - Path-specific limits for high-risk endpoints (auth, build, etc.)
app.add_middleware(IPRateLimitMiddleware)

# Include routers
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(conversations.router)
app.include_router(runs.router)
app.include_router(assets.router)
app.include_router(subscriptions.router)  # Email subscriptions


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Minecraft Mod Generator API - IDE Edition",
        "version": "2.0.0",
        "endpoints": {
            "auth": "/api/auth",
            "workspaces": "/api/workspaces",
            "conversations": "/api/conversations/{id}/messages",
            "runs": "/api/runs",
            "assets": "/api/assets",
            "subscriptions": "/api/subscriptions"
        },
        "docs": "/docs"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "ai": "ready"
    }


if __name__ == "__main__":
    import uvicorn

    print(f"""
    ╔════════════════════════════════════════════════════╗
    ║  Minecraft Mod Generator API - IDE Edition         ║
    ║  AI-Powered Fabric 1.21 Mod Creation               ║
    ╚════════════════════════════════════════════════════╝

    🚀 Starting server...
    📡 API: http://{HOST}:{PORT}
    📖 Docs: http://{HOST}:{PORT}/docs
    🎮 Frontend: http://localhost:8000

    New endpoints (v2):
    - POST /api/workspaces - Create workspace
    - GET  /api/workspaces/{id}/spec - Get mod spec
    - POST /api/conversations/{id}/messages - Send message & trigger run
    - GET  /api/runs/{id}/events - SSE event stream
    - POST /api/runs/workspace/{id}/build - Trigger build

    Press Ctrl+C to stop
    """)

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info"
    )
