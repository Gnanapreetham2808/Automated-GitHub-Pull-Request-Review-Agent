"""
Orchestrator
Coordinates multiple review agents and aggregates their results.
"""

import asyncio
import logging
from typing import Any, Dict, List

from .logic_agent import LogicAgent
from .style_agent import StyleAgent
from .security_agent import SecurityAgent
from .performance_agent import PerformanceAgent

logger = logging.getLogger(__name__)


async def run_agents_on_files(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Run all review agents on a list of files and aggregate results.
    
    Args:
        files: List of file dictionaries, each containing:
            - path: str (file path)
            - hunks: list of dicts with 'header' and 'lines'
    
    Returns:
        List of deduplicated review comment dictionaries
    """
    if not files:
        logger.info("No files to review")
        return []
    
    logger.info(f"Starting orchestrator for {len(files)} files")
    
    # Initialize all agents
    agents = [
        LogicAgent(),
        StyleAgent(),
        SecurityAgent(),
        PerformanceAgent()
    ]
    
    all_comments: List[Dict[str, Any]] = []
    
    # Process each file
    for file_context in files:
        file_path = file_context.get("path", "unknown")
        logger.info(f"Processing file: {file_path}")
        
        # Run all agents concurrently on this file
        agent_tasks = [agent.review(file_context) for agent in agents]
        
        try:
            results = await asyncio.gather(*agent_tasks, return_exceptions=True)
            
            # Collect results from all agents
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"{agents[i].name} failed for {file_path}: {str(result)}")
                    continue
                
                if isinstance(result, list):
                    all_comments.extend(result)
                    logger.debug(f"{agents[i].name} returned {len(result)} comments for {file_path}")
        
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            continue
    
    logger.info(f"Total comments before deduplication: {len(all_comments)}")
    
    # Deduplicate comments
    deduplicated = _deduplicate_comments(all_comments)
    
    logger.info(f"Total comments after deduplication: {len(deduplicated)}")
    
    return deduplicated


def _deduplicate_comments(comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate comments based on path and body similarity.
    
    Args:
        comments: List of comment dictionaries
        
    Returns:
        Deduplicated list of comments
    """
    if not comments:
        return []
    
    seen: Dict[str, Dict[str, Any]] = {}
    
    for comment in comments:
        path = comment.get("path", "")
        body = comment.get("body", "")
        line = comment.get("line", 0)
        
        # Create a key based on path and first 200 chars of body
        body_key = body[:200].strip().lower()
        key = f"{path}:{line}:{body_key}"
        
        # Keep the comment with higher confidence if duplicate
        if key in seen:
            existing_confidence = seen[key].get("confidence", 0.0)
            new_confidence = comment.get("confidence", 0.0)
            
            if new_confidence > existing_confidence:
                seen[key] = comment
                logger.debug(f"Replaced duplicate comment with higher confidence: {key[:50]}...")
        else:
            seen[key] = comment
    
    deduplicated = list(seen.values())
    
    # Sort by file path, then by line number for better organization
    deduplicated.sort(key=lambda x: (x.get("path", ""), x.get("line", 0)))
    
    removed = len(comments) - len(deduplicated)
    if removed > 0:
        logger.info(f"Removed {removed} duplicate comments")
    
    return deduplicated


def _normalize_text(text: str) -> str:
    """
    Normalize text for comparison (lowercase, strip whitespace).
    
    Args:
        text: Input text
        
    Returns:
        Normalized text
    """
    return " ".join(text.lower().split())
