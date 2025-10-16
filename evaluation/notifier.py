 import aiohttp
import asyncio
import logging
from typing import Dict, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

async def notify_evaluation_service(evaluation_url: str, notification_data: BaseModel) -> bool:
    """
    Notify the evaluation service with repository details
    Implements retry logic with exponential backoff
    """
    retry_delays = [1, 2, 4, 8, 16]  # seconds
    
    for attempt, delay in enumerate(retry_delays):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    evaluation_url,
                    json=notification_data.dict(),
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        logger.info("Successfully notified evaluation service")
                        return True
                    else:
                        logger.warning(f"Evaluation service returned status {response.status} on attempt {attempt + 1}")
                        
        except Exception as e:
            logger.warning(f"Failed to notify evaluation service (attempt {attempt + 1}): {str(e)}")
        
        # Wait before retrying (except on last attempt)
        if attempt < len(retry_delays) - 1:
            logger.info(f"Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
    
    logger.error("All attempts to notify evaluation service failed")
    return False