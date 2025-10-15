import os
import google.generativeai as genai
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_application_code(
    brief: str, 
    checks: List[str], 
    attachments: List[str] = None,
    is_update: bool = False
) -> str:
    """
    Generate application code using Gemini Pro based on the brief and requirements
    """
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        if is_update:
            prompt = create_update_prompt(brief, checks, attachments)
        else:
            prompt = create_initial_prompt(brief, checks, attachments)
        
        response = model.generate_content(prompt)
        
        if not response.text:
            raise Exception("No response generated from Gemini")
        
        logger.info("Successfully generated code using Gemini")
        return response.text
        
    except Exception as e:
        logger.error(f"Error generating code with Gemini: {str(e)}")
        # Fallback to template-based generation
        return generate_fallback_code(brief, checks)

def create_initial_prompt(brief: str, checks: List[str], attachments: List[str]) -> str:
    """
    Create prompt for initial application generation
    """
    attachments_info = ""
    if attachments:
        attachments_info = f"\nAttachments available: {', '.join(attachments)}"
    
    return f"""
    Create a complete, production-ready web application based on this brief:
    
    BRIEF: {brief}
    
    REQUIREMENTS:
    {chr(10).join(f'- {check}' for check in checks)}
    {attachments_info}
    
    IMPORTANT INSTRUCTIONS:
    1. Create a SINGLE-PAGE web application (HTML, CSS, JavaScript)
    2. Make it work on GitHub Pages (static hosting)
    3. Include all necessary files: index.html, style.css, script.js
    4. Make it responsive and user-friendly
    5. Include proper error handling
    6. Follow best practices for code structure
    
    OUTPUT FORMAT:
    For each file, use this exact format:
    
    FILENAME: filename.ext
    CONTENT:
    ```file-content-here```
    
    Generate the following files:
    - index.html (main HTML file)
    - style.css (CSS styles)
    - script.js (JavaScript functionality)
    - README.md (project documentation)
    
    Make sure the code is complete and can run directly.
    """

def create_update_prompt(brief: str, checks: List[str], attachments: List[str]) -> str:
    """
    Create prompt for updating existing application
    """
    return f"""
    Update the existing web application with these new requirements:
    
    UPDATE BRIEF: {brief}
    
    NEW REQUIREMENTS:
    {chr(10).join(f'- {check}' for check in checks)}
    
    Update the necessary files while maintaining existing functionality.
    Only output the files that need to be changed.
    
    OUTPUT FORMAT:
    For each modified file, use:
    FILENAME: filename.ext
    CONTENT:
    ```updated-file-content```
    """

def generate_fallback_code(brief: str, checks: List[str]) -> str:
    """
    Generate basic fallback code if LLM fails
    """
    logger.warning("Using fallback code generator")
    
    return """
FILENAME: index.html
CONTENT:
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated App</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>Application</h1>
        <div id="content">
            <p>This app was generated based on: {brief}</p>
        </div>
    </div>
    <script src="script.js"></script>
</body>
</html>

FILENAME: style.css
CONTENT:
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 20px;
    background-color: #f5f5f5;
}

.container {
    max-width: 800px;
    margin: 0 auto;
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

h1 {
    color: #333;
    text-align: center;
}

FILENAME: script.js
CONTENT:
document.addEventListener('DOMContentLoaded', function() {
    console.log('Application loaded');
    // Add your JavaScript functionality here
});

FILENAME: README.md
CONTENT:
# Generated Application

This application was automatically generated.

## Features
- Responsive design
- Modern UI
- Cross-browser compatible

## Setup
Open index.html in a web browser or deploy to GitHub Pages.
    """.format(brief=brief)