"""
Base Agent Abstract Class
Defines the interface and common functionality for all review agents.
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class ReviewComment(BaseModel):
    """Structured review comment model."""
    path: str = Field(..., description="File path")
    line: int = Field(..., gt=0, description="Line number in the diff")
    side: str = Field(..., description="Side of the diff: 'new' or 'old'")
    category: str = Field(..., description="Category of the issue (e.g., logic, style, security)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    body: str = Field(..., min_length=1, description="Review comment text")
    
    @validator("side")
    def validate_side(cls, v: str) -> str:
        """Validate that side is either 'new' or 'old'."""
        if v not in ["new", "old"]:
            return "new"  # Default to new if invalid
        return v


class BaseAgent(ABC):
    """
    Abstract base class for all review agents.
    Defines the interface and common utilities for code review agents.
    """
    
    def __init__(self, name: str, category: str):
        """
        Initialize the agent.
        
        Args:
            name: Human-readable name of the agent
            category: Category of reviews this agent performs
        """
        self.name = name
        self.category = category
        logger.info(f"Initialized {self.name} agent")
    
    @abstractmethod
    async def review(self, file_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Review a file and return structured comments.
        
        Args:
            file_context: Dictionary containing:
                - path: str (file path)
                - hunks: list of dicts with 'header' and 'lines'
        
        Returns:
            List of review comment dictionaries
        """
        pass
    
    def _format_output(self, raw_response: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response and convert to structured review comments.
        
        Args:
            raw_response: Raw JSON string from LLM
            file_path: Path of the file being reviewed
            
        Returns:
            List of structured review comment dictionaries
        """
        try:
            # Try to parse as JSON
            parsed = json.loads(raw_response)
            
            # Handle both single dict and list of dicts
            if isinstance(parsed, dict):
                parsed = [parsed]
            elif not isinstance(parsed, list):
                logger.warning(f"{self.name}: Response is not a list or dict, returning empty")
                return []
            
            comments: List[Dict[str, Any]] = []
            
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                
                # Extract and validate fields
                try:
                    comment = {
                        "path": item.get("path", file_path),
                        "line": int(item.get("line", 1)),
                        "side": item.get("side", "new"),
                        "category": item.get("category", self.category),
                        "confidence": float(item.get("confidence", 0.7)),
                        "body": item.get("body", "").strip()
                    }
                    
                    # Validate required fields
                    if not comment["body"]:
                        continue
                    
                    # Ensure confidence is in valid range
                    comment["confidence"] = max(0.0, min(1.0, comment["confidence"]))
                    
                    # Ensure side is valid
                    if comment["side"] not in ["new", "old"]:
                        comment["side"] = "new"
                    
                    # Validate using pydantic model
                    ReviewComment(**comment)
                    comments.append(comment)
                    
                except (ValueError, KeyError, TypeError) as e:
                    logger.warning(f"{self.name}: Skipping invalid comment: {e}")
                    continue
            
            logger.info(f"{self.name}: Extracted {len(comments)} valid comments")
            return comments
        
        except json.JSONDecodeError:
            logger.warning(f"{self.name}: Failed to parse JSON, attempting fallback")
            return self._fallback_parse(raw_response, file_path)
    
    def _fallback_parse(self, raw_response: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Fallback parser for non-JSON responses.
        Attempts to extract structured information from plain text.
        
        Args:
            raw_response: Raw text response from LLM
            file_path: Path of the file being reviewed
            
        Returns:
            List of review comment dictionaries (may be empty)
        """
        comments: List[Dict[str, Any]] = []
        
        # Try to extract JSON arrays/objects from the text
        json_pattern = r'\[[\s\S]*?\]|\{[\s\S]*?\}'
        matches = re.findall(json_pattern, raw_response)
        
        for match in matches:
            try:
                parsed = json.loads(match)
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict) and "body" in item:
                            comments.append({
                                "path": item.get("path", file_path),
                                "line": int(item.get("line", 1)),
                                "side": item.get("side", "new"),
                                "category": item.get("category", self.category),
                                "confidence": float(item.get("confidence", 0.5)),
                                "body": item.get("body", "").strip()
                            })
                elif isinstance(parsed, dict) and "body" in parsed:
                    comments.append({
                        "path": parsed.get("path", file_path),
                        "line": int(parsed.get("line", 1)),
                        "side": parsed.get("side", "new"),
                        "category": parsed.get("category", self.category),
                        "confidence": float(parsed.get("confidence", 0.5)),
                        "body": parsed.get("body", "").strip()
                    })
            except (json.JSONDecodeError, ValueError, KeyError):
                continue
        
        if comments:
            logger.info(f"{self.name}: Fallback parser extracted {len(comments)} comments")
        else:
            logger.warning(f"{self.name}: Fallback parser found no valid comments")
        
        return comments
    
    def _extract_hunk_snippet(self, hunk: Dict[str, Any], max_lines: int = 60) -> str:
        """
        Extract a snippet from a hunk for LLM analysis.
        
        Args:
            hunk: Hunk dictionary with 'header' and 'lines'
            max_lines: Maximum number of lines to include
            
        Returns:
            Formatted snippet string
        """
        header = hunk.get("header", "")
        lines = hunk.get("lines", [])
        
        # Limit lines
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            truncated = True
        else:
            truncated = False
        
        snippet = f"{header}\n"
        snippet += "\n".join(lines)
        
        if truncated:
            snippet += f"\n... ({len(hunk.get('lines', [])) - max_lines} more lines truncated)"
        
        return snippet
