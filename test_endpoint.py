import httpx
import asyncio
from config import Config
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_endpoint():
    """Test the RunPod endpoint status."""
    try:
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            health_url = f"https://api.runpod.ai/v2/sbcndmp3lkxkwb/health"
            response = await client.get(
                health_url,
                headers=Config.RUNPOD_HEADERS
            )
            
            logger.info("=== Health Check Response ===")
            logger.info(f"Status code: {response.status_code}")
            logger.info(f"Response: {response.text}")
            logger.info("===========================")
            
            if response.status_code == 200:
                status_data = response.json()
                if status_data.get("status") == "ACTIVE":
                    logger.info("Endpoint is active and ready!")
                else:
                    logger.warning(f"Endpoint status is: {status_data.get('status')}")
            else:
                logger.error("Failed to check endpoint status")
                
    except Exception as e:
        logger.error(f"Error testing endpoint: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_endpoint()) 