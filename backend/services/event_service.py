"""
Event Service - Manages run events for SSE streaming

Provides:
- emit_event(): Write event to DB and notify subscribers
- subscribe(): Subscribe to events for a run (SSE generator)
- Event types standardization
"""
import asyncio
import json
import threading
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator, List
from uuid import UUID
from collections import defaultdict

from sqlalchemy.orm import Session
from database import RunEvent, Run, Workspace


# In-memory subscribers for real-time event delivery
# In production, consider using Redis pub/sub for multi-instance support
_subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
_subscribers_lock = threading.Lock()

# Store the main event loop for thread-safe event dispatch
_main_loop: Optional[asyncio.AbstractEventLoop] = None

def set_main_loop(loop: asyncio.AbstractEventLoop):
    """Set the main event loop for thread-safe event dispatch"""
    global _main_loop
    _main_loop = loop


class EventType:
    """Standard event types"""
    # Run lifecycle
    RUN_STATUS = "run.status"  # Status change: queued/running/succeeded/failed/canceled
    RUN_PROGRESS = "run.progress"  # Progress update (0-100)
    RUN_AWAITING_INPUT = "run.awaiting_input"  # Run paused, waiting for user response
    RUN_AWAITING_APPROVAL = "run.awaiting_approval"  # Run paused, waiting for user to approve/reject deltas
    
    # Logging
    LOG_APPEND = "log.append"  # Log message
    LOG_ERROR = "log.error"  # Error log
    
    # Spec changes
    SPEC_PREVIEW = "spec.preview"  # Preview of spec changes (not saved)
    SPEC_PATCH = "spec.patch"  # Partial spec update applied
    SPEC_SAVED = "spec.saved"  # Full spec saved
    
    # Asset events
    ASSET_GENERATED = "asset.generated"  # New asset generated (texture candidate)
    ASSET_SELECTED = "asset.selected"  # Asset selected by user

    # Texture selection events
    TEXTURE_SELECTION_REQUIRED = "texture.selection_required"  # Run paused, waiting for user to select texture variant
    TEXTURE_SELECTED = "texture.selected"  # User selected a texture variant
    
    # Artifact events
    ARTIFACT_CREATED = "artifact.created"  # New artifact available (JAR, etc.)
    
    # Pipeline task events
    TASK_STARTED = "task.started"  # Pipeline task started
    TASK_FINISHED = "task.finished"  # Pipeline task finished


def emit_event(
    db: Session,
    run_id: UUID,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    update_workspace: bool = True
) -> RunEvent:
    """
    Emit an event for a run
    
    - Writes event to database
    - Notifies real-time subscribers
    - Updates workspace last_modified_at if requested
    
    Args:
        db: Database session
        run_id: Run ID
        event_type: Event type (use EventType constants)
        payload: Event payload data
        update_workspace: Whether to update workspace.last_modified_at
    
    Returns:
        Created RunEvent
    """
    # Create event record
    event = RunEvent(
        run_id=run_id,
        event_type=event_type,
        payload=payload or {}
    )
    db.add(event)
    
    # Update workspace last_modified_at if requested
    if update_workspace:
        run = db.query(Run).filter(Run.id == run_id).first()
        if run and run.workspace_id:
            workspace = db.query(Workspace).filter(Workspace.id == run.workspace_id).first()
            if workspace:
                workspace.last_modified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(event)
    
    # Notify real-time subscribers
    _notify_subscribers(str(run_id), event)
    
    return event


def emit_event_sync(
    db: Session,
    run_id: UUID,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None
) -> RunEvent:
    """
    Synchronous version of emit_event for use in background tasks
    
    Writes event to DB AND notifies real-time subscribers.
    """
    event = RunEvent(
        run_id=run_id,
        event_type=event_type,
        payload=payload or {}
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    # Also notify real-time subscribers (put_nowait is non-blocking, safe from sync code)
    _notify_subscribers(str(run_id), event)
    
    return event


def _notify_subscribers(run_id: str, event: RunEvent):
    """
    Notify all subscribers for a run about a new event.
    Thread-safe: can be called from background threads.
    """
    event_data = {
            "id": str(event.id),
            "run_id": str(event.run_id),
            "event_type": event.event_type,
            "payload": event.payload,
            "created_at": event.created_at.isoformat() if event.created_at else None
    }
    
    with _subscribers_lock:
        if run_id not in _subscribers:
            return
        queues = list(_subscribers[run_id])  # Copy to avoid holding lock during put
    
    for queue in queues:
        try:
            # Try to use the event loop's thread-safe method if available
            if _main_loop and _main_loop.is_running():
                _main_loop.call_soon_threadsafe(
                    lambda q=queue, d=event_data: _safe_put(q, d)
                )
            else:
                # Fallback to direct put (works if called from event loop thread)
                queue.put_nowait(event_data)
        except Exception as e:
            # Log but don't fail - subscriber might have disconnected
            print(f"[EventService] Warning: Failed to notify subscriber: {e}")


def _safe_put(queue: asyncio.Queue, data: dict):
    """Safely put data into queue, ignore if full"""
    try:
        queue.put_nowait(data)
    except asyncio.QueueFull:
        pass


async def subscribe(run_id: str) -> AsyncGenerator[str, None]:
    """
    Subscribe to events for a run (SSE generator)
    
    Yields SSE-formatted event strings.
    
    Usage:
        @router.get("/api/runs/{run_id}/events")
        async def get_events(run_id: str):
            return StreamingResponse(
                subscribe(run_id),
                media_type="text/event-stream"
            )
    """
    # Set the main event loop for thread-safe event dispatch
    global _main_loop
    try:
        _main_loop = asyncio.get_running_loop()
    except RuntimeError:
        pass
    
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    
    # Thread-safe add subscriber
    with _subscribers_lock:
        _subscribers[run_id].append(queue)
    
    try:
        # Send initial connection event
        yield f": connected to run {run_id}\n\n"
        
        while True:
            try:
                # Wait for new event with timeout
                event_data = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"event: {event_data['event_type']}\n"
                yield f"data: {json.dumps(event_data)}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive comment to keep connection alive
                yield ": keepalive\n\n"
    except asyncio.CancelledError:
        pass
    except GeneratorExit:
        pass
    finally:
        # Thread-safe cleanup subscriber
        with _subscribers_lock:
            if run_id in _subscribers:
                try:
                    _subscribers[run_id].remove(queue)
                except ValueError:
                    pass
            if not _subscribers[run_id]:
                del _subscribers[run_id]


def get_events_since(
    db: Session,
    run_id: UUID,
    since_id: Optional[UUID] = None,
    limit: int = 100
) -> List[RunEvent]:
    """
    Get events for a run since a given event ID
    
    Useful for catching up on missed events after reconnection.
    """
    query = db.query(RunEvent).filter(RunEvent.run_id == run_id)
    
    if since_id:
        # Get the timestamp of the since event
        since_event = db.query(RunEvent).filter(RunEvent.id == since_id).first()
        if since_event:
            query = query.filter(RunEvent.created_at > since_event.created_at)
    
    return query.order_by(RunEvent.created_at).limit(limit).all()


# Convenience functions for common event types

def emit_status_change(
    db: Session,
    run_id: UUID,
    status: str,
    progress: Optional[int] = None
) -> RunEvent:
    """Emit a status change event"""
    payload = {"status": status}
    if progress is not None:
        payload["progress"] = progress
    return emit_event(db, run_id, EventType.RUN_STATUS, payload)


def emit_log(
    db: Session,
    run_id: UUID,
    message: str,
    level: str = "info"
) -> RunEvent:
    """Emit a log event"""
    return emit_event(
        db, run_id, EventType.LOG_APPEND,
        {"message": message, "level": level},
        update_workspace=False  # Don't update workspace for logs
    )


def emit_spec_preview(
    db: Session,
    run_id: UUID,
    spec_delta: Dict[str, Any]
) -> RunEvent:
    """Emit a spec preview event (candidate changes)"""
    return emit_event(db, run_id, EventType.SPEC_PREVIEW, {"delta": spec_delta})


def emit_artifact_created(
    db: Session,
    run_id: UUID,
    artifact_id: UUID,
    artifact_type: str,
    file_name: str,
    download_url: Optional[str] = None
) -> RunEvent:
    """Emit an artifact created event"""
    return emit_event(
        db, run_id, EventType.ARTIFACT_CREATED,
        {
            "artifact_id": str(artifact_id),
            "artifact_type": artifact_type,
            "file_name": file_name,
            "download_url": download_url
        }
    )

