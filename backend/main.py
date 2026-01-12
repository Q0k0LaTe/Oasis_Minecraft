"""
FastAPI Backend for Minecraft Mod Generator
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import HOST, PORT, CORS_ORIGINS
from routers import auth, jobs, jobs_v2, sessions

# Initialize FastAPI app
app = FastAPI(
    title="Minecraft Mod Generator API",
    description="AI-powered Minecraft Fabric mod generator",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,  # Allow credentials for cookies/auth headers
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(jobs_v2.router)  # New pipeline-based API (V2)
app.include_router(sessions.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Minecraft Mod Generator API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth",
            "jobs": "/api/generate-mod",
            "jobs_v2": "/api/v2/generate",
            "sessions": "/api/sessions"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "ai": "ready"
    }


if __name__ == "__main__":
    import uvicorn

    print(f"""
    ╔════════════════════════════════════════════════╗
    ║  Minecraft Mod Generator API                   ║
    ║  AI-Powered Fabric 1.21 Mod Creation          ║
    ╚════════════════════════════════════════════════╝

    🚀 Starting server...
    📡 API: http://{HOST}:{PORT}
    📖 Docs: http://{HOST}:{PORT}/docs
    🎮 Frontend: http://localhost:8000

    Press Ctrl+C to stop
    """)

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info"
    )
