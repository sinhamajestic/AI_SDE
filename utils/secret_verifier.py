 import os
import logging

logger = logging.getLogger(__name__)

def verify_secret(secret: str) -> bool:
    """
    Verify if the provided secret matches the expected secret
    """
    expected_secret = os.getenv("STUDENT_SECRET")
    
    if not expected_secret:
        logger.error("STUDENT_SECRET environment variable not set")
        return False
    
    if secret == expected_secret:
        logger.info("Secret verification successful")
        return True
    else:
        logger.warning(f"Secret verification failed. Expected: {expected_secret[:5]}..., Got: {secret[:5]}...")
        return False