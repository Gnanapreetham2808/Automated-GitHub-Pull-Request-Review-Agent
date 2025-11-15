"""
Style Agent
Reviews code for readability, naming conventions, and maintainability.
"""

import logging
from typing import Any, Dict, List

from .base_agent import BaseAgent
from .llm_client import llm_call, LLMError

logger = logging.getLogger(__name__)


class StyleAgent(BaseAgent):
    """
    Agent specialized in code style and maintainability.
    Focuses on: readability, naming, formatting, code organization.
    """
    
    SYSTEM_PROMPT = """You are an expert code reviewer specializing in code style and maintainability.

Analyze the provided code diff and identify:
- Poor variable/function naming
- Complex or unclear code that needs refactoring
- Missing documentation or comments where needed
- Inconsistent formatting or style
- Code duplication
- Overly long functions or classes
- Poor code organization

Return ONLY a JSON array of issues. Each issue must have:
{
  "path": "file/path",
  "line": <line_number>,
  "side": "new",
  "category": "style",
  "confidence": <0.0-1.0>,
  "body": "Brief explanation of the style issue"
}

If no issues found, return: []"""
    
    def __init__(self):
        """Initialize the Style Agent."""
        super().__init__(name="StyleAgent", category="style")
    
    async def review(self, file_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Review a file for style and maintainability issues.
        
        Args:
            file_context: Dictionary containing 'path' and 'hunks'
            
        Returns:
            List of review comment dictionaries
        """
        file_path = file_context.get("path", "unknown")
        hunks = file_context.get("hunks", [])
        
        if not hunks:
            logger.debug(f"{self.name}: No hunks to review for {file_path}")
            return []
        
        all_comments: List[Dict[str, Any]] = []
        
        for hunk in hunks:
            try:
                snippet = self._extract_hunk_snippet(hunk, max_lines=60)
                
                user_prompt = f"""File: {file_path}

Code changes:
```
{snippet}
```

Review this code change for style and maintainability issues."""
                
                logger.debug(f"{self.name}: Reviewing hunk in {file_path}")
                
                response = await llm_call(
                    system_prompt=self.SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    model="gpt-4o-mini",
                    temperature=0.3
                )
                
                comments = self._format_output(response, file_path)
                all_comments.extend(comments)
                
            except LLMError as e:
                logger.error(f"{self.name}: LLM error for {file_path}: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"{self.name}: Unexpected error for {file_path}: {str(e)}")
                continue
        
        logger.info(f"{self.name}: Found {len(all_comments)} issues in {file_path}")
        return all_comments
