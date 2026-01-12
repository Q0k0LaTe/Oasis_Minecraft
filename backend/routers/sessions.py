"""
Sessions router
FastAPI routes for conversation session management
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# TODO: Implement session management endpoints
# - POST /api/sessions/new - Create new session
# - GET /api/sessions - List all sessions
# - GET /api/sessions/{session_id} - Get session details with jobs
# - PATCH /api/sessions/{session_id} - Update session name
# - DELETE /api/sessions/{session_id} - Delete session

