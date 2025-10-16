import os
import re
import google.generativeai as genai
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_and_parse_code(brief: str, checks: List[str], attachments: List[str] = None, is_update: bool = False) -> List[Dict]:
    try:
        model = genai.GenerativeModel('gemini-2.5-pro')
        prompt = _create_prompt(brief, checks, attachments, is_update)
        response = model.generate_content(prompt)

        if not response.text:
            raise Exception("No response generated from Gemini")
        
        logger.info("Successfully generated code using Gemini")
        return _parse_code_output(response.text)

    except Exception as e:
        logger.error(f"Error generating code with Gemini: {str(e)}")
        return _parse_code_output(generate_fallback_code(brief, checks))

def _create_prompt(brief: str, checks: List[str], attachments: List[str], is_update: bool) -> str:
    attachments_info = f"\nAttachments available: {', '.join(attachments)}" if attachments else ""
    
    if is_update:
        return f"""
        Update the existing web application with these new requirements:
        UPDATE BRIEF: {brief}
        NEW REQUIREMENTS:
        {chr(10).join(f'- {check}' for check in checks)}
        
        Only output the files that need to be changed.
        OUTPUT FORMAT:
        For each modified file, use:
        FILENAME: filename.ext
        CONTENT:
        ```updated-file-content```
        """
    
    return f"""
    Create a complete, production-ready web application based on this brief:
    BRIEF: {brief}
    REQUIREMENTS:
    {chr(10).join(f'- {check}' for check in checks)}
    {attachments_info}
    
    IMPORTANT INSTRUCTIONS:
    1. Create a SINGLE-PAGE web application (HTML, CSS, JavaScript)
    2. Make it work on GitHub Pages (static hosting)
    3. Include all necessary files: index.html, style.css, script.js, README.md
    
    OUTPUT FORMAT:
    For each file, use this exact format:
    FILENAME: filename.ext
    CONTENT:
    ```file-content-here```
    """

def _parse_code_output(generated_output: str) -> List[Dict]:
    files = []
    file_blocks = re.split(r'FILENAME:\s*', generated_output)
    
    for block in file_blocks:
        if not block.strip():
            continue
        
        parts = block.split('CONTENT:', 1)
        if len(parts) == 2:
            filename = parts[0].strip()
            content = parts[1].strip().replace('```', '')
            files.append({"path": filename, "content": content})
            logger.info(f"Parsed file: {filename}")
            
    return files

def generate_fallback_code(brief: str, checks: List[str]) -> str:
    logger.warning("Using fallback code generator")
    return f"""
FILENAME: index.html
CONTENT:
<!DOCTYPE html>
<html>
<body>
    <h1>Application</h1>
    <p>Brief: {brief}</p>
</body>
</html>

FILENAME: style.css
CONTENT:
body {{ font-family: sans-serif; }}

FILENAME: script.js
CONTENT:
console.log('Application loaded');

FILENAME: README.md
CONTENT:
# Generated Application
This application was automatically generated.
"""