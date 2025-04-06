import json
import httpx
import sys
import os
import asyncio
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_workflow():
    try:
        print("Loading workflow from Tempest Workflow.json...")
        with open("Tempest Workflow.json", "r") as f:
            workflow = json.load(f)
            print("Workflow loaded successfully.")

        # Generate a random seed for the noise node
        random_seed = random.randint(0, 2**32 - 1)
        print(f"Using random seed: {random_seed}")
        workflow["99"]["inputs"]["noise_seed"] = random_seed

        # Generate a unique content request ID
        content_request_id = f"test_{random.randint(10000000, 99999999)}"

        print("\nSubmitting workflow to executor service...")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    'http://127.0.0.1:8001/execute-workflow',
                    json={
                        "workflow": workflow,
                        "content_request_id": content_request_id
                    },
                    headers={
                        "Content-Type": "application/json"
                    },
                    timeout=300.0  # 5 minutes timeout for long-running workflows
                )
                
                response.raise_for_status()
                result = response.json()
                print(f"\nResponse status code: {response.status_code}")
                print(f"Content request ID: {content_request_id}")
                print("Workflow is being processed...")
                print("Result:", result)  # Print the full result for debugging
                
            except httpx.ConnectError as e:
                print(f"Failed to connect to the server: {e}")
                print("Make sure the FastAPI server is running on port 8001.")
                sys.exit(1)
            except httpx.TimeoutException as e:
                print(f"Request timed out: {e}")
                print("The workflow might be taking longer than expected (>5 minutes).")
                sys.exit(1)
            except httpx.HTTPError as e:
                print(f"HTTP error occurred: {e}")
                print(f"Response: {e.response.text if hasattr(e, 'response') else 'No response'}")
                sys.exit(1)
                
    except FileNotFoundError:
        print("Error: Tempest Workflow.json not found!")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in workflow file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        print("Traceback:")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_workflow()) 