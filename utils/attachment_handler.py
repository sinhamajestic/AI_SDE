 import os
import base64
import uuid
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def handle_attachments(attachments: List[Dict]) -> List[str]:
    """
    Process attachments from data URIs and save them as files
    Returns list of file paths
    """
    saved_files = []
    
    for attachment in attachments:
        try:
            file_path = save_data_uri_to_file(
                data_uri=attachment["url"],
                filename=attachment["name"]
            )
            saved_files.append(file_path)
            logger.info(f"Saved attachment: {attachment['name']}")
        except Exception as e:
            logger.error(f"Failed to process attachment {attachment['name']}: {str(e)}")
    
    return saved_files

def save_data_uri_to_file(data_uri: str, filename: str) -> str:
    """
    Convert data URI to file and save it
    """
    # Extract the base64 data from the data URI
    if ',' in data_uri:
        header, data = data_uri.split(',', 1)
    else:
        data = data_uri
    
    # Decode base64 data
    file_data = base64.b64decode(data)
    
    # Create attachments directory if it doesn't exist
    attachments_dir = "attachments"
    os.makedirs(attachments_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(attachments_dir, filename)
    with open(file_path, 'wb') as f:
        f.write(file_data)
    
    return file_path