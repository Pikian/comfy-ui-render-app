import os
import json
import httpx
import asyncio
import websockets
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
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
supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

app = FastAPI()

class WorkflowRequest(BaseModel):
    workflow: dict
    content_request_id: str

class WorkflowExecutor:
    def __init__(self):
        self.output_dir = Config.OUTPUT_DIR
        
    async def execute_workflow(self, workflow_json: dict, content_request_id: str) -> dict:
        """Execute a workflow and return the result."""
        try:
            # Queue the workflow
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{Config.COMFYUI_API_URL}/prompt",
                    json={"prompt": workflow_json}
                )
                response.raise_for_status()
                prompt_id = response.json()["prompt_id"]
                logger.info(f"Workflow queued with ID: {prompt_id}")

            # Wait for completion
            execution_completed = False
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries and not execution_completed:
                try:
                    async with websockets.connect(Config.COMFYUI_WS_URL) as websocket:
                        await websocket.send(json.dumps({"prompt_id": prompt_id}))
                        
                        while True:
                            message = await websocket.recv()
                            data = json.loads(message)
                            
                            if data["type"] == "status":
                                # Check if the queue is empty and our prompt is done
                                if "data" in data and "status" in data["data"]:
                                    status = data["data"]["status"]
                                    if "exec_info" in status:
                                        queue_remaining = status["exec_info"].get("queue_remaining", 1)
                                        if queue_remaining == 0:
                                            execution_completed = True
                                            break
                            
                            elif data["type"] == "error":
                                error = data["data"]["error"]
                                raise Exception(f"Workflow execution failed: {error}")
                                
                except (websockets.exceptions.ConnectionClosedError, ConnectionRefusedError) as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"Connection error (attempt {retry_count}/{max_retries}): {e}")
                        await asyncio.sleep(2)
                    else:
                        raise Exception(f"Failed to connect to ComfyUI after {max_retries} attempts: {e}")

            if not execution_completed:
                raise Exception("Workflow execution did not complete successfully")

            # Get the generated image
            async with httpx.AsyncClient() as client:
                # Get history to find the image
                history_response = await client.get(f"{Config.COMFYUI_API_URL}/history")
                history_response.raise_for_status()
                history = history_response.json()
                
                if prompt_id not in history:
                    raise Exception("Workflow not found in history")
                
                # Find the SaveImage node's output
                output_images = history[prompt_id]["outputs"]
                for node_id, node_output in output_images.items():
                    if "images" in node_output:
                        for image_info in node_output["images"]:
                            # Download the image from ComfyUI
                            image_url = f"{Config.COMFYUI_API_URL}/view?filename={image_info['filename']}&subfolder={image_info['subfolder']}&type={image_info['type']}"
                            image_response = await client.get(image_url)
                            image_response.raise_for_status()
                            image_data = image_response.content
                            
                            # Generate UUID for the image
                            image_uuid = str(uuid.uuid4())
                            
                            # Create the proper path structure
                            supabase_path = f"comfyui-output/{content_request_id}/{image_uuid}.png"
                            
                            # Save to local folder first
                            local_path = self.output_dir / f"{content_request_id}_{image_uuid}.png"
                            with open(local_path, "wb") as f:
                                f.write(image_data)
                            
                            # Upload to Supabase with the new path structure
                            try:
                                with open(local_path, "rb") as f:
                                    response = supabase.storage.from_("media").upload(
                                        supabase_path,
                                        f.read(),
                                        {"content-type": "image/png"}
                                    )
                                
                                # Get the public URL
                                image_url = supabase.storage.from_("media").get_public_url(supabase_path)
                                logger.info(f"Image uploaded successfully: {image_url}")
                                
                                # Clean up local file
                                local_path.unlink()
                                
                                return {
                                    "status": "completed",
                                    "image_url": image_url,
                                    "content_request_id": content_request_id,
                                    "image_uuid": image_uuid
                                }
                                
                            except Exception as upload_error:
                                logger.error(f"Failed to upload to Supabase: {upload_error}")
                                raise Exception(f"Failed to upload image to Supabase: {upload_error}")
                
                raise Exception("No output images found in workflow history")
                
        except Exception as e:
            logger.error(f"Error executing workflow: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

executor = WorkflowExecutor()

@app.post("/execute-workflow")
async def execute_workflow(request: WorkflowRequest):
    logger.info("Received workflow execution request")
    logger.info(f"Starting workflow execution for content_request_id: {request.content_request_id}")
    result = await executor.execute_workflow(request.workflow, request.content_request_id)
    logger.info(f"Workflow execution completed for content_request_id: {request.content_request_id}")
    return result

if __name__ == "__main__":
    import uvicorn
    # Validate configuration
    Config.validate()
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host=Config.HOST, port=Config.PORT) 