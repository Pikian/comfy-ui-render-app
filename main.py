import os
import json
import httpx
import asyncio
import websockets
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import uuid
from config import Config

# Configure logging
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)

app = FastAPI()

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

class WorkflowRequest(BaseModel):
    workflow: dict
    content_request_id: str

class WorkflowExecutor:
    def __init__(self):
        self.output_dir = Config.OUTPUT_DIR
        
    async def execute_workflow(self, workflow_json: dict, content_request_id: str) -> dict:
        """Execute a workflow, upload the image, and update the Supabase DB."""
        try:
            # Queue the workflow
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{Config.COMFYUI_API_URL}/prompt",
                    json={"prompt": workflow_json}
                )
                response.raise_for_status()
                prompt_id = response.json()["prompt_id"]
                logger.info(f"Workflow queued with ID: {prompt_id} for request {content_request_id}")

            # Wait for completion using WebSocket
            execution_completed = False
            max_retries = 3
            retry_count = 0
            current_node = None # Track current node

            while retry_count < max_retries and not execution_completed:
                try:
                    async with websockets.connect(Config.COMFYUI_WS_URL) as websocket:
                        logger.info(f"WebSocket connected for prompt {prompt_id}")
                        # Not sending prompt_id, assuming we listen for all messages
                        # await websocket.send(json.dumps({"prompt_id": prompt_id}))
                        
                        while True:
                            message = await websocket.recv()
                            data = json.loads(message)
                            msg_type = data.get("type")
                            msg_data = data.get("data", {})

                            if msg_type == "status":
                                status = msg_data.get("status", {})
                                queue_remaining = status.get("exec_info", {}).get("queue_remaining", 1)
                                logger.debug(f"Status update for {content_request_id}: Queue remaining: {queue_remaining}")
                                if queue_remaining == 0:
                                    # Check history to confirm our prompt finished
                                    async with httpx.AsyncClient() as hist_client:
                                        history_response = await hist_client.get(f"{Config.COMFYUI_API_URL}/history/{prompt_id}")
                                        if history_response.status_code == 200:
                                            logger.info(f"Confirmed execution completed for prompt {prompt_id} via history API.")
                                            execution_completed = True
                                            break # Exit inner websocket loop
                                        else:
                                            logger.debug(f"Queue empty but prompt {prompt_id} not in history yet. Waiting...")

                            elif msg_type == "executing":
                                node_id = msg_data.get("node")
                                received_prompt_id = msg_data.get("prompt_id")
                                if received_prompt_id == prompt_id:
                                     current_node = node_id
                                     logger.info(f"Node {node_id} is executing for prompt {prompt_id}.")
                                     if node_id is None: # Check if execution finished for this prompt
                                         logger.info(f"Execution finished message received for prompt {prompt_id}.")
                                         # We still rely on queue_remaining == 0 check for final completion

                            elif msg_type == "progress":
                                progress = msg_data.get("value", 0)
                                total = msg_data.get("max", 1)
                                logger.debug(f"Progress update for {content_request_id}: Node {current_node} - {progress}/{total}")
                            
                            elif msg_type == "execution_error":
                                exec_prompt_id = msg_data.get("prompt_id")
                                if exec_prompt_id == prompt_id:
                                    error_info = msg_data.get("error", {})
                                    exception_message = msg_data.get("exception_message", "Unknown error")
                                    logger.error(f"Execution error for prompt {prompt_id}: {exception_message}", exc_info=True)
                                    raise Exception(f"Workflow execution failed: {exception_message}")

                            elif msg_type == "executed":
                                exec_prompt_id = msg_data.get("prompt_id")
                                if exec_prompt_id == prompt_id:
                                    node_id = msg_data.get("node")
                                    outputs = msg_data.get("output", {})
                                    logger.info(f"Node {node_id} finished execution for prompt {prompt_id}.")
                                    # Final completion is checked via status message (queue_remaining=0) and history

                except (websockets.exceptions.ConnectionClosedError, ConnectionRefusedError) as e:
                    retry_count += 1
                    logger.warning(f"WebSocket connection error (attempt {retry_count}/{max_retries}): {e}")
                    if retry_count >= max_retries:
                        raise Exception(f"Failed to connect to ComfyUI WebSocket after {max_retries} attempts: {e}")
                    await asyncio.sleep(2) # Wait before retrying connection
                except Exception as ws_err: # Catch other WebSocket processing errors
                     logger.error(f"Error processing WebSocket message for {content_request_id}: {ws_err}")
                     raise # Re-raise to be caught by the outer try-except

            if not execution_completed:
                logger.error(f"Workflow execution did not complete successfully for prompt {prompt_id}.")
                raise Exception("Workflow execution timed out or failed to confirm completion.")

            # --- Post-Execution: Get Image and Update Supabase ---
            logger.info(f"Fetching results for completed prompt {prompt_id}...")
            async with httpx.AsyncClient() as client:
                history_response = await client.get(f"{Config.COMFYUI_API_URL}/history/{prompt_id}")
                history_response.raise_for_status()
                history = history_response.json()

                if prompt_id not in history:
                    raise Exception(f"Workflow prompt {prompt_id} not found in history after completion.")

                output_images = history[prompt_id].get("outputs", {})
                image_found = False
                for node_id, node_output in output_images.items():
                    if "images" in node_output:
                        for image_info in node_output["images"]:
                            image_found = True
                            logger.info(f"Found image output from node {node_id}: {image_info['filename']}")
                            # Download the image from ComfyUI
                            image_url_comfy = f"{Config.COMFYUI_API_URL}/view?filename={image_info['filename']}&subfolder={image_info.get('subfolder', '')}&type={image_info['type']}"
                            image_response = await client.get(image_url_comfy)
                            image_response.raise_for_status()
                            image_data = image_response.content

                            # Generate UUID for the image
                            image_uuid = str(uuid.uuid4())
                            supabase_path = f"comfyui-output/{content_request_id}/{image_uuid}.png"

                            # Upload to Supabase Storage
                            try:
                                response = supabase.storage.from_("media").upload(
                                    supabase_path,
                                    image_data, # Upload bytes directly
                                    {"content-type": "image/png"}
                                )
                                supabase_image_url = supabase.storage.from_("media").get_public_url(supabase_path)
                                logger.info(f"Image uploaded successfully to Supabase: {supabase_image_url}")

                                # Update Supabase DB
                                try:
                                    # Fetch current assets
                                    current_data_response = supabase.table("content_requests").select("assets").eq("id", content_request_id).execute()
                                    if not current_data_response.data:
                                         raise Exception(f"Content request ID {content_request_id} not found in DB.")

                                    current_assets = current_data_response.data[0].get("assets", {})
                                    if not isinstance(current_assets, dict): # Handle null or non-dict assets
                                        current_assets = {}
                                    
                                    # Add image URL to assets
                                    current_assets["image_url"] = supabase_image_url

                                    # Update row
                                    update_response = supabase.table("content_requests").update({
                                        "status": "ready",
                                        "assets": current_assets
                                    }).eq("id", content_request_id).execute()

                                    # Check for update errors (optional but recommended)
                                    # if update_response.error:
                                    #     logger.error(f"Failed to update DB for {content_request_id}: {update_response.error}")
                                    #     raise Exception(f"DB update failed: {update_response.error}")
                                    # else:
                                    logger.info(f"Successfully updated content_requests table for ID: {content_request_id}, Status: ready")

                                    return {
                                        "status": "completed", # Middleware status
                                        "image_url": supabase_image_url,
                                        "content_request_id": content_request_id,
                                        "image_uuid": image_uuid
                                    }

                                except Exception as db_update_error:
                                     logger.error(f"Failed to update Supabase DB for {content_request_id}: {db_update_error}")
                                     # Mark as failed even if image uploaded, as DB update is crucial
                                     raise Exception(f"Failed to update database after image upload: {db_update_error}")


                            except Exception as upload_error:
                                logger.error(f"Failed to upload image to Supabase Storage for {content_request_id}: {upload_error}")
                                raise Exception(f"Failed to upload image to Supabase: {upload_error}")

                            break # Process only the first found image
                    if image_found:
                        break

                if not image_found:
                    raise Exception("No output images found in workflow history.")

        except Exception as e:
            logger.error(f"Error executing workflow for {content_request_id}: {e}", exc_info=True)
            # Update Supabase DB status to "cancelled"
            try:
                update_response = supabase.table("content_requests").update({
                    "status": "cancelled"
                }).eq("id", content_request_id).execute()
                logger.info(f"Successfully updated content_requests table for ID: {content_request_id}, Status: cancelled")
            except Exception as db_error:
                logger.error(f"Failed to update Supabase DB status to 'cancelled' for {content_request_id}: {db_error}")

            # Return failure status
            return {
                "status": "failed", # Middleware status
                "error": str(e),
                "content_request_id": content_request_id
            }

executor = WorkflowExecutor()

@app.post("/execute-workflow")
async def execute_workflow_endpoint(request: WorkflowRequest):
    logger.info(f"Received workflow execution request for ID: {request.content_request_id}")
    # Don't await here, run in background
    asyncio.create_task(executor.execute_workflow(request.workflow, request.content_request_id))
    logger.info(f"Workflow execution task created for ID: {request.content_request_id}")
    # Return immediately to avoid Vercel timeout
    return {
        "status": "processing",
        "message": "Workflow execution started in the background.",
        "content_request_id": request.content_request_id
    }

if __name__ == "__main__":
    import uvicorn
    # Validate configuration
    Config.validate()
    logger.info("Starting FastAPI server...")
    uvicorn.run("main:app", host=Config.HOST, port=Config.PORT, reload=True) # Added reload=True for dev

    # Validate configuration
    Config.validate()
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host=Config.HOST, port=Config.PORT) 