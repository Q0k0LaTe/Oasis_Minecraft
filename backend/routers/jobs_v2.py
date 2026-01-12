"""
Jobs Router V2 - Updated to use the new pipeline architecture

This version uses the new ModGenerationPipeline while maintaining compatibility
with the existing API structure.
"""
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path

from config import DOWNLOADS_DIR
from models import ItemPromptRequest
from agents.pipeline import ModGenerationPipeline

router = APIRouter(prefix="/api/v2", tags=["jobs-v2"])

# Job tracking (in production, use Redis or database)
jobs = {}


def append_job_log(job_id: str, message: str) -> None:
    """Append a log entry while keeping an upper bound."""
    job = jobs.get(job_id)
    if not job:
        return
    logs = job.setdefault("logs", [])
    logs.append(message)
    if len(logs) > 150:
        job["logs"] = logs[-150:]


def run_generation_task_v2(job_id: str, request_payload: dict):
    """
    Background task to run mod generation using the new pipeline

    This uses the complete pipeline:
    Orchestrator → SpecManager → Compiler → Planner → Executor → Validator → Builder
    """
    try:
        prompt = request_payload.get("prompt")

        if not prompt:
            raise ValueError("Prompt is required")

        # Update job status
        jobs[job_id].update({"status": "processing", "progress": 5})
        append_job_log(job_id, f"Starting mod generation for: {prompt}")

        # Create progress callback
        def progress_callback(msg: str):
            append_job_log(job_id, msg)

            # Update progress based on keywords in message
            if "Phase 1" in msg or "Converting prompt" in msg:
                jobs[job_id].update({"progress": 10})
            elif "Phase 2" in msg or "Applying delta" in msg:
                jobs[job_id].update({"progress": 20})
            elif "Phase 3" in msg or "Compiling" in msg:
                jobs[job_id].update({"progress": 30})
            elif "Phase 4" in msg or "Planning" in msg:
                jobs[job_id].update({"progress": 40})
            elif "Phase 5" in msg or "Executing tasks" in msg:
                jobs[job_id].update({"progress": 50})
            elif "Phase 6" in msg or "Validating" in msg:
                jobs[job_id].update({"progress": 70})
            elif "Phase 7" in msg or "Building" in msg:
                jobs[job_id].update({"progress": 80})

        # Create and run pipeline
        pipeline = ModGenerationPipeline(job_id=job_id)

        result = pipeline.generate_mod(
            user_prompt=prompt,
            conversation_history=[],
            progress_callback=progress_callback
        )

        if result["status"] == "success":
            # Build successful response
            jar_path = result["jar_path"]
            jar_file = Path(jar_path)

            full_result = {
                "success": True,
                "jobId": job_id,
                "modId": result["mod_id"],
                "modName": result["mod_name"],
                "downloadUrl": f"/api/v2/download/{job_id}",
                "jarFile": jar_file.name,
                "specVersion": result["spec_version"],
                "message": "Mod generated successfully!",
                "executionLog": result.get("execution_log", [])
            }

            jobs[job_id].update({
                "status": "completed",
                "progress": 100,
                "result": full_result,
                "jar_path": jar_path
            })
            append_job_log(job_id, f"✓ Job completed successfully! JAR: {jar_file.name}")

        else:
            # Build failed
            error_msg = result.get("error", "Unknown error")
            jobs[job_id].update({
                "status": "failed",
                "progress": 100,
                "error": error_msg,
                "result": {
                    "success": False,
                    "error": error_msg,
                    "executionLog": result.get("execution_log", [])
                }
            })
            append_job_log(job_id, f"✗ Job failed: {error_msg}")

    except Exception as e:
        print(f"Error in generation task: {e}")
        import traceback
        traceback.print_exc()

        jobs[job_id].update({
            "status": "failed",
            "progress": 100,
            "error": str(e)
        })
        append_job_log(job_id, f"Critical Error: {str(e)}")


@router.post("/generate")
async def generate_mod_v2(request: ItemPromptRequest, background_tasks: BackgroundTasks):
    """
    Generate a mod using the new pipeline (V2)

    This endpoint uses the new architecture:
    - Pipeline orchestration
    - Tool registry
    - IR-based generation
    """
    job_id = str(uuid.uuid4())

    # Initialize job
    jobs[job_id] = {
        "jobId": job_id,
        "status": "pending",
        "progress": 0,
        "logs": [],
        "result": None,
        "error": None
    }

    # Prepare request payload
    request_payload = {
        "prompt": request.prompt,
        "authorName": request.authorName,
        "modName": request.modName
    }

    # Start background task
    background_tasks.add_task(run_generation_task_v2, job_id, request_payload)

    return {
        "success": True,
        "jobId": job_id,
        "message": "Mod generation started"
    }


@router.get("/status/{job_id}")
async def get_job_status_v2(job_id: str):
    """Get status of a generation job"""
    job = jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "jobId": job_id,
        "status": job.get("status"),
        "progress": job.get("progress", 0),
        "logs": job.get("logs", []),
        "result": job.get("result"),
        "error": job.get("error")
    }


@router.get("/download/{job_id}")
async def download_mod_v2(job_id: str):
    """Download the generated mod JAR file"""
    job = jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    jar_path = job.get("jar_path")

    if not jar_path or not Path(jar_path).exists():
        raise HTTPException(status_code=404, detail="JAR file not found")

    return FileResponse(
        path=jar_path,
        media_type="application/java-archive",
        filename=Path(jar_path).name
    )


@router.get("/logs/{job_id}")
async def get_job_logs_v2(job_id: str):
    """Get detailed logs for a job"""
    job = jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "jobId": job_id,
        "logs": job.get("logs", []),
        "status": job.get("status")
    }


__all__ = ["router"]
