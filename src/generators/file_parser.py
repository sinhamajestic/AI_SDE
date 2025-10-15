import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def parse_code_output(generated_output: str) -> List[Dict]:
    """
    Parse LLM output into structured file objects
    """
    files = []
    
    # Split by FILENAME pattern
    file_blocks = re.split(r'FILENAME:\s*', generated_output)
    
    for block in file_blocks:
        if not block.strip():
            continue
            
        # Extract filename and content
        lines = block.strip().split('\n')
        if not lines:
            continue
            
        filename = lines[0].strip()
        content_lines = []
        
        # Find content start (look for CONTENT: marker)
        in_content = False
        for line in lines[1:]:
            if line.strip().startswith('CONTENT:'):
                in_content = True
                # Remove the CONTENT: marker but keep the rest
                content_line = line.replace('CONTENT:', '', 1).strip()
                if content_line:
                    content_lines.append(content_line)
                continue
            elif in_content:
                # Remove code block markers if present
                clean_line = line.replace('```', '')
                content_lines.append(clean_line)
        
        content = '\n'.join(content_lines).strip()
        
        if filename and content:
            files.append({
                "path": filename,
                "content": content
            })
            logger.info(f"Parsed file: {filename} ({len(content)} chars)")
    
    # Ensure we have at least basic files
    required_files = ['index.html', 'style.css', 'script.js', 'README.md']
    existing_files = [f['path'] for f in files]
    
    for req_file in required_files:
        if req_file not in existing_files:
            logger.warning(f"Missing required file: {req_file}")
    
    return files