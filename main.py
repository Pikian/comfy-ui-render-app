import asyncio
import httpx
import logging
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
from config import Config
import json
from supabase import create_client, Client
import uuid
import time
import base64
from io import BytesIO
from PIL import Image

# Configure logging with more detailed format
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log configuration at startup
logger.debug("Configuration loaded:")
logger.debug(f"RunPod API URL: {Config.RUNPOD_API_URL}")
logger.debug(f"RunPod Endpoint ID: {Config.RUNPOD_ENDPOINT_ID}")
logger.debug(f"Supabase URL: {Config.SUPABASE_URL}")
logger.debug(f"Server Host: {Config.HOST}")
logger.debug(f"Server Port: {Config.PORT}")

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client
try:
    supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")
    raise

class WorkflowRequest(BaseModel):
    workflow: Dict[str, Any]
    content_request_id: str
    user_id: Optional[str] = "default_user"

async def check_job_status(job_id: str) -> Dict[str, Any]:
    """Check the status of a RunPod job."""
    logger.debug(f"Checking status for job {job_id}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{Config.RUNPOD_API_URL}/status/{job_id}",
                headers=Config.RUNPOD_HEADERS
            )
            status_data = response.json()
            logger.debug(f"Job {job_id} status: {status_data}")
            return status_data
    except Exception as e:
        logger.error(f"Error checking job status: {str(e)}")
        raise

async def process_image_data(image_data: str) -> bytes:
    """Process base64 image data from RunPod."""
    try:
        logger.debug("Processing image data")
        # Remove the data URL prefix if present
        if image_data.startswith('data:image/'):
            logger.debug("Removing data URL prefix")
            image_data = image_data.split(',')[1]
        
        # Decode base64 data
        logger.debug("Decoding base64 data")
        image_bytes = base64.b64decode(image_data)
        
        # Convert to PNG if needed
        logger.debug("Opening image with PIL")
        image = Image.open(BytesIO(image_bytes))
        if image.format != 'PNG':
            logger.debug(f"Converting image from {image.format} to PNG")
            output = BytesIO()
            image.save(output, format='PNG')
            image_bytes = output.getvalue()
        
        logger.debug(f"Image processed successfully, size: {len(image_bytes)} bytes")
        return image_bytes
    except Exception as e:
        logger.error(f"Error processing image data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process image data: {str(e)}")

async def upload_to_supabase(image_data: bytes, user_id: str, content_request_id: str) -> str:
    """Upload image to Supabase storage."""
    try:
        # Create structured path
        path = f"{user_id}/{content_request_id}/image.png"
        logger.debug(f"Uploading image to Supabase path: {path}")
        
        # Upload to Supabase
        supabase.storage.from_("images").upload(
            path=path,
            file=image_data,
            file_options={"content-type": "image/png"}
        )
        logger.debug("Image uploaded successfully")
        
        # Get public URL
        url = supabase.storage.from_("images").get_public_url(path)
        logger.debug(f"Image public URL: {url}")
        return url
    except Exception as e:
        logger.error(f"Supabase upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")

@app.post("/execute-workflow")
async def execute_workflow(request: WorkflowRequest):
    """Execute a workflow using RunPod's ComfyUI service."""
    try:
        logger.info(f"Received workflow execution request: {request.content_request_id}")
        logger.debug(f"User ID: {request.user_id}")
        logger.debug(f"Workflow: {json.dumps(request.workflow, indent=2)}")
        
        # Submit job to RunPod
        async with httpx.AsyncClient() as client:
            logger.debug("Submitting job to RunPod")
            response = await client.post(
                f"{Config.RUNPOD_API_URL}/run",
                headers=Config.RUNPOD_HEADERS,
                json={"input": {"workflow": request.workflow}},
                timeout=Config.RUNPOD_TIMEOUT
            )
            
            if response.status_code != 200:
                error_msg = f"RunPod API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise HTTPException(status_code=response.status_code, detail=error_msg)
            
            job_data = response.json()
            job_id = job_data["id"]
            logger.info(f"Job submitted successfully. Job ID: {job_id}")
            
            # Poll for job completion
            start_time = time.time()
            while time.time() - start_time < Config.RUNPOD_TIMEOUT:
                status = await check_job_status(job_id)
                logger.debug(f"Job status: {status}")
                
                if status["status"] == "COMPLETED":
                    logger.info(f"Job {job_id} completed successfully")
                    # Get image data from RunPod output
                    if "output" not in status or "image" not in status["output"]:
                        error_msg = f"No image data in RunPod output: {status}"
                        logger.error(error_msg)
                        raise HTTPException(status_code=500, detail=error_msg)
                    
                    # Process and upload the image
                    image_bytes = await process_image_data(status["output"]["image"])
                    image_url = await upload_to_supabase(
                        image_bytes,
                        request.user_id,
                        request.content_request_id
                    )
                    
                    logger.info(f"Workflow execution completed successfully: {image_url}")
                    return {
                        "status": "success",
                        "image_url": image_url,
                        "content_request_id": request.content_request_id,
                        "job_id": job_id
                    }
                
                elif status["status"] == "FAILED":
                    error_msg = f"Job {job_id} failed: {status.get('error', 'Unknown error')}"
                    logger.error(error_msg)
                    raise HTTPException(status_code=500, detail=error_msg)
                
                await asyncio.sleep(Config.STATUS_CHECK_INTERVAL)
            
            error_msg = f"Job {job_id} timed out after {Config.RUNPOD_TIMEOUT} seconds"
            logger.error(error_msg)
            raise HTTPException(status_code=408, detail=error_msg)
            
    except httpx.RequestError as e:
        error_msg = f"RunPod API error: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.websocket("/ws/{content_request_id}")
async def websocket_endpoint(websocket: WebSocket, content_request_id: str):
    """WebSocket endpoint for real-time updates."""
    logger.info(f"WebSocket connection requested for content_request_id: {content_request_id}")
    await websocket.accept()
    try:
        while True:
            # Check job status
            status = await check_job_status(content_request_id)
            await websocket.send_json(status)
            logger.debug(f"Sent status update for {content_request_id}: {status}")
            
            if status["status"] in ["COMPLETED", "FAILED"]:
                logger.info(f"WebSocket connection closing for {content_request_id}: {status['status']}")
                break
                
            await asyncio.sleep(Config.STATUS_CHECK_INTERVAL)
    except Exception as e:
        logger.error(f"WebSocket error for {content_request_id}: {str(e)}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host=Config.HOST, port=Config.PORT) 