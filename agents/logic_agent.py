"""
Logic Agent
Reviews code for correctness, logic errors, and edge cases.
"""

import logging
from typing import Any, Dict, List

from .base_agent import BaseAgent
from .llm_client import llm_call, LLMError

logger = logging.getLogger(__name__)


class LogicAgent(BaseAgent):
    """
    Agent specialized in detecting logic errors and correctness issues.
    Focuses on: off-by-one errors, undefined behavior, missed conditions, etc.
    """
    
    SYSTEM_PROMPT = """You are an expert code reviewer specializing in logic and correctness.

Analyze the provided code diff and identify:
- Off-by-one errors
- Null/undefined reference issues
- Missing edge case handling
- Incorrect conditional logic
- Type mismatches or coercion issues
- Potential infinite loops or recursion
- Logic errors in algorithms

Return ONLY a JSON array of issues. Each issue must have:
{
  "path": "file/path",
  "line": <line_number>,
  "side": "new",
  "category": "logic",
  "confidence": <0.0-1.0>,
  "body": "Brief explanation of the logic issue"
}

If no issues found, return: []"""
    
    def __init__(self):
        """Initialize the Logic Agent."""
        super().__init__(name="LogicAgent", category="logic")
    
    async def review(self, file_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Review a file for logic and correctness issues.
        
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

Review this code change for logic errors and correctness issues."""
                
                logger.debug(f"{self.name}: Reviewing hunk in {file_path}")
                
                response = await llm_call(
                    system_prompt=self.SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    model="gemini-1.5-flash",
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
