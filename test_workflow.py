import os
import json
import time
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
RUNPOD_API_KEY = os.getenv('RUNPOD_API_KEY')
RUNPOD_ENDPOINT_ID = os.getenv('RUNPOD_ENDPOINT_ID')

if not RUNPOD_API_KEY or not RUNPOD_ENDPOINT_ID:
    raise ValueError("RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID must be set")

# Constants
API_BASE_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}"
HEADERS = {
    "Authorization": f"Bearer {RUNPOD_API_KEY}",
    "Content-Type": "application/json"
}

def load_workflow(filename: str = "BASICFLUX_WORKFLOW.json") -> Dict[str, Any]:
    try:
        with open(filename, 'r') as f:
            workflow = json.load(f)
            
        logger.info("=== Workflow Structure ===")
        logger.info(f"Total nodes: {len(workflow)}")
        logger.info("Key nodes:")
        
        # Log important nodes
        for node_id, node in workflow.items():
            if node['class_type'] in ['CheckpointLoaderSimple', 'LoraLoader', 'SaveImage']:
                logger.info(f"Node {node_id}: {node['class_type']}")
                logger.info(f"Inputs: {json.dumps(node['inputs'], indent=2)}")
        
        logger.info("=======================")
        return workflow
    except Exception as e:
        logger.error(f"Error loading workflow: {str(e)}")
        raise

def validate_model_paths(workflow: Dict[str, Any]) -> None:
    """Validate model paths in the workflow"""
    logger.info("=== Validating Model Paths ===")
    
    for node_id, node in workflow.items():
        if node['class_type'] == 'CheckpointLoaderSimple':
            checkpoint_path = node['inputs'].get('ckpt_name', '')
            logger.info(f"Checkpoint path: {checkpoint_path}")
            if not checkpoint_path.endswith('.safetensors'):
                logger.warning(f"Unexpected checkpoint path: {checkpoint_path}")
                
        elif node['class_type'] == 'LoraLoader':
            lora_name = node['inputs'].get('lora_name', '')
            logger.info(f"LoRA path: {lora_name}")
            
    logger.info("=== Model Path Validation Complete ===")

def submit_workflow(workflow_data):
    url = f"{API_BASE_URL}/run"
    payload = {
        "input": {
            "workflow": workflow_data  # Changed from "prompt" to "workflow"
        }
    }
    logging.info(f"Making POST request to: {url}")
    logging.info(f"Request data: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        logging.info("=== Response ===")
        logging.info(f"Status code: {response.status_code}")
        logging.info(f"Headers: {response.headers}")
        logging.info(f"Text: {response.text}")
        logging.info("===============")
        
        if response.status_code == 200:
            job_id = response.json().get("id")
            logging.info(f"Job submitted successfully. Job ID: {job_id}")
            return job_id
        else:
            logging.error(f"Failed to submit job. Status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            return None
    except Exception as e:
        logging.error(f"Error submitting workflow: {str(e)}")
        return None

def check_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Check status of a submitted job"""
    url = f"{API_BASE_URL}/status/{job_id}"
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        data = response.json()
        status = data.get('status')
        logger.info(f"Job status: {status}")
        
        if status == "COMPLETED":
            return data.get('output')
        elif status == "FAILED":
            error = data.get('error', 'Unknown error')
            logger.error(f"Error details: {error}")
            return None
        else:
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking job status: {str(e)}")
        if hasattr(e.response, 'text'):
            logger.error(f"Response text: {e.response.text}")
        return None

def main():
    try:
        # Load and validate workflow
        workflow = load_workflow()
        validate_model_paths(workflow)
        
        # Submit workflow
        job_id = submit_workflow(workflow)
        
        # Monitor job status
        retries = 30  # 5 minutes total
        while retries > 0:
            status = check_job_status(job_id)
            
            if status is not None:
                logger.info(f"Workflow completed successfully")
                logger.info(f"Output: {json.dumps(status, indent=2)}")
                break
                
            logger.info("Workflow is still processing...")
            time.sleep(10)  # Wait 10 seconds between checks
            retries -= 1
            
        if retries == 0:
            logger.error("Workflow timed out")
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main() 