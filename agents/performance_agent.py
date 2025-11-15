"""
Performance Agent
Reviews code for performance issues and inefficiencies.
"""

import logging
from typing import Any, Dict, List

from .base_agent import BaseAgent
from .llm_client import llm_call, LLMError

logger = logging.getLogger(__name__)


class PerformanceAgent(BaseAgent):
    """
    Agent specialized in performance optimization.
    Focuses on: algorithmic inefficiencies, DB query loops, unnecessary computation.
    """
    
    SYSTEM_PROMPT = """You are an expert performance optimization code reviewer.

Analyze the provided code diff and identify:
- Inefficient algorithms or data structures
- N+1 query problems in database operations
- Unnecessary loops or redundant computations
- Memory leaks or excessive memory usage
- Blocking operations in async code
- Inefficient string concatenation
- Missing caching opportunities
- Inefficient I/O operations
- Unnecessary network calls

Return ONLY a JSON array of issues. Each issue must have:
{
  "path": "file/path",
  "line": <line_number>,
  "side": "new",
  "category": "performance",
  "confidence": <0.0-1.0>,
  "body": "Brief explanation of the performance issue"
}

If no issues found, return: []"""
    
    def __init__(self):
        """Initialize the Performance Agent."""
        super().__init__(name="PerformanceAgent", category="performance")
    
    async def review(self, file_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Review a file for performance issues.
        
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

Review this code change for performance issues and optimization opportunities."""
                
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
