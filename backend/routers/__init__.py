"""
Routers package
FastAPI route handlers organized by domain
"""
from . import auth
from . import workspaces
from . import conversations
from . import runs
from . import assets
# Legacy V2 API (kept for backward compatibility)
from . import jobs_v2

__all__ = [
    "auth",
    "workspaces",
    "conversations",
    "runs",
    "assets",
    "jobs_v2",
]
