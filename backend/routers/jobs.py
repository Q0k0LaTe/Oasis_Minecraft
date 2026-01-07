"""
Jobs router
FastAPI routes for mod generation jobs
"""
import base64
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from config import DOWNLOADS_DIR
from models import ItemPromptRequest
from agents.mod_analyzer import ModAnalyzerAgent
from agents.mod_generator import ModGenerator
from agents.tools.image_generator import ImageGenerator

router = APIRouter(prefix="/api", tags=["jobs"])

# Initialize agents
analyzer = ModAnalyzerAgent()
generator = ModGenerator()

# Store for tracking generation jobs (in production, use Redis or database)
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


def continue_generation_after_selection(job_id: str):
    """Continue generation after user has selected images"""
    job = jobs.get(job_id)
    if not job:
        return

    try:
        spec = job.get("spec", {})
        selections = job.get("selections", {})

        # Use selected images to continue with mod generation
        append_job_log(job_id, "Finalizing assets with selected textures...")

        # Call ModGenerator with selected images
        def on_progress(msg):
            append_job_log(job_id, msg)

        # Create a modified generator that uses the selected images
        generator = ModGenerator()
        generation_result = generator.generate_mod_with_selected_images(
            spec,
            job_id,
            selections,
            progress_callback=on_progress
        )

        if not generation_result["success"]:
            jobs[job_id].update({
                "status": "failed",
                "progress": 100,
                "error": generation_result.get("error")
            })
            append_job_log(job_id, f"Error: {generation_result.get('error')}")
            return

        # Build final result
        entry_payload = compose_entry_payload_with_selections(spec, generation_result, selections)
        entry_payload["message"] = "Mod generated successfully!"
        full_result = {
            "success": True,
            "jobId": job_id,
            **entry_payload
        }

        jobs[job_id].update({
            "status": "completed",
            "progress": 100,
            "result": full_result
        })
        append_job_log(job_id, "Job completed successfully.")

    except Exception as e:
        print(f"Error continuing generation: {e}")
        import traceback
        traceback.print_exc()
        jobs[job_id].update({
            "status": "failed",
            "progress": 100,
            "error": str(e)
        })
        append_job_log(job_id, f"Critical Error: {str(e)}")


def compose_entry_payload_with_selections(ai_spec, generation_result, selections):
    """Compose payload with selected images"""
    interactive = ai_spec.get("interactive")
    block_spec = ai_spec.get("block")
    tool_spec = ai_spec.get("tool")
    packaging_plan = ai_spec.get("packagingPlan")

    return {
        "aiDecisions": {
            "modName": ai_spec["modName"],
            "modId": ai_spec["modId"],
            "itemName": ai_spec["itemName"],
            "itemId": ai_spec["itemId"],
            "description": ai_spec["description"],
            "author": ai_spec["author"],
            "properties": ai_spec["properties"],
            "interactive": interactive,
            "block": block_spec,
            "tool": tool_spec,
            "packagingPlan": packaging_plan,
        },
        "downloadUrl": generation_result.get("downloadUrl"),
        "textureBase64": selections.get("item"),
        "blockTextureBase64": selections.get("block"),
        "toolTextureBase64": selections.get("tool"),
        "message": "Entry generated successfully!",
    }


def run_generation_task(job_id: str, request_payload: dict):
    """Background task to run either a single prompt or a curated worklist."""

    def compose_entry_payload(ai_spec, generation_result):
        interactive = ai_spec.get("interactive")
        block_spec = ai_spec.get("block")
        tool_spec = ai_spec.get("tool")
        packaging_plan = ai_spec.get("packagingPlan")

        return {
            "aiDecisions": {
                "modName": ai_spec["modName"],
                "modId": ai_spec["modId"],
                "itemName": ai_spec["itemName"],
                "itemId": ai_spec["itemId"],
                "description": ai_spec["description"],
                "author": ai_spec["author"],
                "properties": ai_spec["properties"],
                "interactive": interactive,
                "block": block_spec,
                "tool": tool_spec,
                "packagingPlan": packaging_plan,
            },
            "downloadUrl": generation_result.get("downloadUrl"),
            "textureBase64": generation_result.get("textureBase64"),
            "blockTextureBase64": generation_result.get("blockTextureBase64"),
            "toolTextureBase64": generation_result.get("toolTextureBase64"),
            "message": "Entry generated successfully!",
        }

    try:
        worklist = request_payload.get("worklist") or []
        prompt = request_payload.get("prompt")
        author_name = request_payload.get("authorName")
        mod_name = request_payload.get("modName")

        if worklist:
            total_entries = len(worklist)
            append_job_log(job_id, f"Starting batch generation with {total_entries} entries...")
            batch_results = []

            for index, entry in enumerate(worklist, start=1):
                entry_prompt = (entry.get("prompt") or "").strip()
                entry_kind = (entry.get("kind") or "ITEM").upper()
                entry_author = entry.get("authorName") or author_name
                entry_mod_override = entry.get("modName") or mod_name
                entry_id = entry.get("id") or str(uuid.uuid4())
                entry_label = f"{entry_kind.title()} {index}/{total_entries}"

                if not entry_prompt:
                    append_job_log(job_id, f"[{entry_label}] Skipped: missing prompt.")
                    continue

                jobs[job_id].update({"status": "analyzing", "progress": max(5, int(((index - 1) / total_entries) * 40))})
                append_job_log(job_id, f"[{entry_label}] Analyzing prompt with AI agent...")
                ai_spec = analyzer.analyze(
                    user_prompt=entry_prompt,
                    author_name=entry_author,
                    mod_name_override=entry_mod_override,
                )

                jobs[job_id].update({
                    "status": "generating",
                    "progress": max(35, int(((index - 1) / total_entries) * 70)),
                    "spec": ai_spec
                })
                append_job_log(job_id, f"[{entry_label}] Generating code and assets...")

                def progress_cb(message, label=entry_label):
                    append_job_log(job_id, f"[{label}] {message}")

                generation_result = generator.generate_mod(ai_spec, job_id, progress_callback=progress_cb)
                if not generation_result["success"]:
                    raise RuntimeError(f"{entry_label} failed: {generation_result.get('error')}")

                entry_payload = compose_entry_payload(ai_spec, generation_result)
                entry_payload.update({
                    "worklistId": entry_id,
                    "kind": entry_kind,
                })
                batch_results.append(entry_payload)
                jobs[job_id].update({"progress": int((index / total_entries) * 90)})

            if not batch_results:
                raise ValueError("No valid worklist entries were provided.")

            main_entry = batch_results[0]
            full_result = {
                "success": True,
                "jobId": job_id,
                "batchResults": batch_results,
                # Backwards-compatible fields for existing UI code paths
                "aiDecisions": main_entry.get("aiDecisions"),
                "downloadUrl": main_entry.get("downloadUrl"),
                "textureBase64": main_entry.get("textureBase64"),
                "blockTextureBase64": main_entry.get("blockTextureBase64"),
                "toolTextureBase64": main_entry.get("toolTextureBase64"),
                "message": f"Generated {len(batch_results)} worklist entries."
            }

            jobs[job_id].update({
                "status": "completed",
                "progress": 100,
                "result": full_result
            })
            append_job_log(job_id, f"Batch job completed: {len(batch_results)} entries ready.")
            return

        if not prompt:
            raise ValueError("Prompt is required when the worklist is empty.")

        jobs[job_id].update({"status": "analyzing", "progress": 10})
        append_job_log(job_id, "Analyzing prompt with AI agent...")
        print(f"[Job {job_id}] Analyzing prompt: {prompt}")

        ai_spec = analyzer.analyze(
            user_prompt=prompt,
            author_name=author_name,
            mod_name_override=mod_name
        )

        print(f"[Job {job_id}] AI decisions: {ai_spec}")
        jobs[job_id].update({
            "status": "generating_images",
            "progress": 35,
            "spec": ai_spec
        })
        append_job_log(job_id, f"Plan: Creating {ai_spec['itemName']} in mod {ai_spec['modId']}")

        # Generate multiple image options for user to choose from
        append_job_log(job_id, "Generating 5 texture options for each asset...")

        image_gen = ImageGenerator()
        pending_selections = {}

        # Generate item textures
        append_job_log(job_id, f"Generating textures for {ai_spec['itemName']}...")
        item_textures = image_gen.generate_multiple_item_textures(
            item_description=ai_spec.get("description", ""),
            item_name=ai_spec.get("itemName", "Item"),
            count=5
        )
        pending_selections["item"] = {
            "name": ai_spec.get("itemName"),
            "options": [base64.b64encode(t).decode("utf-8") for t in item_textures]
        }

        # Generate block textures if block exists
        block_spec = ai_spec.get("block")
        if block_spec:
            append_job_log(job_id, f"Generating textures for {block_spec.get('blockName')}...")
            block_textures = image_gen.generate_multiple_block_textures(block_spec, count=5)
            pending_selections["block"] = {
                "name": block_spec.get("blockName"),
                "options": [base64.b64encode(t).decode("utf-8") for t in block_textures]
            }

        # Generate tool textures if tool exists
        tool_spec = ai_spec.get("tool")
        if tool_spec:
            append_job_log(job_id, f"Generating textures for {tool_spec.get('toolName')}...")
            tool_textures = image_gen.generate_multiple_tool_textures(tool_spec, count=5)
            pending_selections["tool"] = {
                "name": tool_spec.get("toolName"),
                "options": [base64.b64encode(t).decode("utf-8") for t in tool_textures]
            }

        # Pause for user to select images
        jobs[job_id].update({
            "status": "awaiting_image_selection",
            "progress": 50,
            "pendingImageSelection": pending_selections
        })
        append_job_log(job_id, "Image options generated. Waiting for your selection...")

        # Job will wait here until user selects images via /api/jobs/{job_id}/select-image
        # The endpoint will call continue_generation_after_selection() when ready
        return

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


@router.post("/generate-mod")
async def generate_mod(request: ItemPromptRequest, background_tasks: BackgroundTasks):
    """
    Start a background job to generate a Minecraft mod.
    Returns a Job ID immediately.
    """
    job_id = str(uuid.uuid4())
    
    # Initialize job
    jobs[job_id] = {
        "status": "queued", 
        "progress": 0, 
        "logs": ["Job queued..."],
        "spec": None,
        "result": None
    }
    
    # Start background task
    background_tasks.add_task(
        run_generation_task,
        job_id,
        request.model_dump()
    )
    
    return {
        "success": True,
        "jobId": job_id,
        "message": "Generation started"
    }


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """Get the status of a generation job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return jobs[job_id]


@router.get("/downloads/{filename}")
async def download_mod(filename: str):
    """Download a generated mod file"""
    file_path = DOWNLOADS_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/java-archive"
    )


@router.post("/jobs/{job_id}/select-image")
async def select_image(job_id: str, selection: dict, background_tasks: BackgroundTasks):
    """
    Handle user's image selection

    Expected payload:
    {
        "assetType": "item"|"block"|"tool",
        "selectedIndex": 0-4
    }
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job["status"] != "awaiting_image_selection":
        raise HTTPException(status_code=400, detail="Job is not waiting for image selection")

    # Store the selection
    asset_type = selection.get("assetType")
    selected_index = selection.get("selectedIndex")

    if asset_type not in ["item", "block", "tool"]:
        raise HTTPException(status_code=400, detail="Invalid asset type")

    if not isinstance(selected_index, int) or selected_index < 0 or selected_index >= 5:
        raise HTTPException(status_code=400, detail="Invalid selection index")

    # Get the pending selection data
    pending = job.get("pendingImageSelection", {})
    if asset_type not in pending:
        raise HTTPException(status_code=400, detail="No images awaiting selection for this asset type")

    # Store the selected image
    selected_image = pending[asset_type]["options"][selected_index]
    if "selections" not in job:
        job["selections"] = {}
    job["selections"][asset_type] = selected_image

    # Check if all required selections are complete
    pending_types = list(pending.keys())
    selected_types = list(job.get("selections", {}).keys())

    if set(pending_types) == set(selected_types):
        # All selections complete, resume generation
        job["status"] = "generating"
        job["pendingImageSelection"] = {}
        append_job_log(job_id, "Image selections complete, resuming generation...")

        # Continue generation in background
        background_tasks.add_task(continue_generation_after_selection, job_id)

    return {"success": True, "message": "Image selected"}


@router.post("/jobs/{job_id}/regenerate-images")
async def regenerate_images(job_id: str, request: dict):
    """
    Regenerate 5 new image options for a specific asset type

    Expected payload:
    {
        "assetType": "item"|"block"|"tool"
    }
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job["status"] != "awaiting_image_selection":
        raise HTTPException(status_code=400, detail="Job is not waiting for image selection")

    asset_type = request.get("assetType")
    if asset_type not in ["item", "block", "tool"]:
        raise HTTPException(status_code=400, detail="Invalid asset type")

    pending = job.get("pendingImageSelection", {})
    if asset_type not in pending:
        raise HTTPException(status_code=400, detail="No images to regenerate for this asset type")

    # Regenerate images
    append_job_log(job_id, f"Regenerating {asset_type} textures...")

    image_gen = ImageGenerator()

    spec = job.get("spec", {})
    new_images = []

    try:
        if asset_type == "item":
            textures = image_gen.generate_multiple_item_textures(
                item_description=spec.get("description", ""),
                item_name=spec.get("itemName", "Item"),
                count=5
            )
            new_images = [base64.b64encode(t).decode("utf-8") for t in textures]

        elif asset_type == "block":
            block_spec = spec.get("block")
            if block_spec:
                textures = image_gen.generate_multiple_block_textures(block_spec, count=5)
                new_images = [base64.b64encode(t).decode("utf-8") for t in textures]

        elif asset_type == "tool":
            tool_spec = spec.get("tool")
            if tool_spec:
                textures = image_gen.generate_multiple_tool_textures(tool_spec, count=5)
                new_images = [base64.b64encode(t).decode("utf-8") for t in textures]

        # Update the pending selection with new images
        pending[asset_type]["options"] = new_images
        append_job_log(job_id, f"Generated {len(new_images)} new {asset_type} textures")

        return {
            "success": True,
            "images": new_images
        }

    except Exception as e:
        append_job_log(job_id, f"Error regenerating {asset_type} images: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate images: {str(e)}")

