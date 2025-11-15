"""
Review API Routes
Handles manual diff and GitHub PR review endpoints with multi-agent orchestration.
"""

import asyncio
import logging
import time
from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator

from agents.orchestrator import run_agents_on_files
from agents.llm_client import llm_call, LLMError

logger = logging.getLogger("review")

# Configure router
router = APIRouter(prefix="/review", tags=["Review"])


# ==================== Pydantic Models ====================

class ManualReviewRequest(BaseModel):
    """Request model for manual diff review."""
    diff: str = Field(..., min_length=1, description="Raw unified diff text")

    @validator("diff")
    def validate_diff_not_empty(cls, v: str) -> str:
        """Validate that diff is not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Diff cannot be empty or whitespace only")
        return v


class GithubReviewRequest(BaseModel):
    """Request model for GitHub PR review."""
    owner: str = Field(..., min_length=1, description="GitHub repository owner")
    repo: str = Field(..., min_length=1, description="GitHub repository name")
    pr: int = Field(..., gt=0, description="Pull request number")

    @validator("owner", "repo")
    def validate_not_empty(cls, v: str) -> str:
        """Validate that owner and repo are not empty."""
        if not v or not v.strip():
            raise ValueError("Owner and repo cannot be empty")
        return v.strip()


class ReviewComment(BaseModel):
    """Model for individual review comment."""
    path: str = Field(..., description="File path")
    line: int = Field(..., description="Line number")
    side: str = Field(..., description="Side of diff: 'new' or 'old'")
    category: str = Field(..., description="Review category (logic, style, security, performance)")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)")
    body: str = Field(..., description="Review comment text")


class ReviewResponse(BaseModel):
    """Response model for review endpoints."""
    comments: List[ReviewComment] = Field(..., description="List of review comments")
    summary: Optional[str] = Field(None, description="High-level summary of findings")


# ==================== Helper Functions ====================

def parse_unified_diff(diff: str) -> List[dict]:
    """
    Parse a unified diff string into structured format.
    
    Args:
        diff: Raw unified diff text
        
    Returns:
        List of file dictionaries with path and hunks
        
    Raises:
        ValueError: If diff is empty or invalid
    """
    import re
    
    if not diff or not diff.strip():
        raise ValueError("Diff cannot be empty")
    
    files: List[dict] = []
    lines = diff.split("\n")
    
    current_file: Optional[str] = None
    current_hunks: List[dict] = []
    current_hunk_header: Optional[str] = None
    current_hunk_lines: List[str] = []
    
    def save_current_hunk() -> None:
        """Helper to save the current hunk being processed."""
        if current_hunk_header is not None and current_hunk_lines:
            current_hunks.append({
                "header": current_hunk_header,
                "lines": current_hunk_lines.copy()
            })
    
    def save_current_file() -> None:
        """Helper to save the current file being processed."""
        if current_file is not None and current_hunks:
            files.append({
                "path": current_file,
                "hunks": current_hunks.copy()
            })
    
    for line in lines:
        # Check for file header (diff --git a/... b/...)
        if line.startswith("diff --git"):
            save_current_hunk()
            save_current_file()
            
            current_file = None
            current_hunks = []
            current_hunk_header = None
            current_hunk_lines = []
            
        # Extract file path from +++ b/...
        elif line.startswith("+++ b/"):
            current_file = line[6:]
            
        # Extract file path from --- a/... (fallback)
        elif line.startswith("--- a/") and current_file is None:
            current_file = line[6:]
            
        # Check for hunk header (@@ ... @@)
        elif line.startswith("@@"):
            save_current_hunk()
            
            match = re.match(r"^(@@[^@]+@@)", line)
            if match:
                current_hunk_header = match.group(1)
                current_hunk_lines = []
            
        # Process hunk content lines
        elif current_hunk_header is not None:
            if line.startswith(("+", "-", " ")):
                current_hunk_lines.append(line)
            elif line and not line.startswith("\\"):
                if current_hunk_lines:
                    current_hunk_lines.append(f" {line}")
    
    # Save last hunk and file
    save_current_hunk()
    save_current_file()
    
    logger.info(f"Parsed {len(files)} files from diff")
    return files


async def fetch_github_pr_diff(owner: str, repo: str, pr_number: int) -> str:
    """
    Fetch pull request diff from GitHub API.
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        
    Returns:
        Raw diff text
        
    Raises:
        HTTPException: If GitHub API call fails or token is missing
    """
    import os
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable not set")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub token not configured. Set GITHUB_TOKEN environment variable."
        )
    
    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"Fetching PR metadata: {owner}/{repo}#{pr_number}")
            response = await client.get(api_url, headers=headers)
            
            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pull request #{pr_number} not found in {owner}/{repo}"
                )
            elif response.status_code == 403:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="GitHub API rate limit exceeded or access forbidden"
                )
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"GitHub API error: {response.status_code}"
                )
            
            pr_data = response.json()
            diff_url = pr_data.get("diff_url")
            
            if not diff_url:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="diff_url not found in PR response"
                )
            
            logger.info(f"Fetching diff from: {diff_url}")
            diff_response = await client.get(diff_url, headers=headers)
            
            if diff_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to fetch diff: {diff_response.status_code}"
                )
            
            diff_text = diff_response.text
            
            if not diff_text or not diff_text.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Pull request has no diff (empty or no changes)"
                )
            
            logger.info(f"Successfully fetched diff ({len(diff_text)} bytes)")
            return diff_text
            
    except httpx.TimeoutException:
        logger.error("GitHub API request timed out")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="GitHub API request timed out"
        )
    except httpx.RequestError as e:
        logger.error(f"GitHub API request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to GitHub API: {str(e)}"
        )


async def generate_summary(comments: List[dict]) -> Optional[str]:
    """
    Generate a high-level summary of review findings using LLM.
    
    Args:
        comments: List of review comment dictionaries
        
    Returns:
        Summary text or None if generation fails
    """
    if not comments:
        return "No issues found in the code review."
    
    # Group comments by category
    categories = {}
    for comment in comments:
        cat = comment.get("category", "other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(comment)
    
    # Build summary prompt
    summary_lines = []
    for category, items in categories.items():
        summary_lines.append(f"- {category.capitalize()}: {len(items)} issue(s)")
    
    prompt = f"""Based on this code review analysis:

{chr(10).join(summary_lines)}

Total issues found: {len(comments)}

Provide a brief 2-3 sentence summary highlighting the most critical findings."""
    
    try:
        summary = await llm_call(
            system_prompt="You are a code review summarizer. Provide concise, actionable summaries.",
            user_prompt=prompt,
            model="gpt-4o-mini",
            temperature=0.3
        )
        return summary.strip()
    except LLMError as e:
        logger.warning(f"Failed to generate summary: {str(e)}")
        return None


async def run_orchestrator_with_timeout(files: List[dict], timeout: float = 120.0) -> List[dict]:
    """
    Run orchestrator with timeout protection.
    
    Args:
        files: List of file dictionaries to review
        timeout: Timeout in seconds
        
    Returns:
        List of review comments
        
    Raises:
        asyncio.TimeoutError: If orchestrator times out
    """
    try:
        return await asyncio.wait_for(
            run_agents_on_files(files),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error(f"Orchestrator timed out after {timeout}s")
        raise


# ==================== API Endpoints ====================

@router.post("/manual", response_model=ReviewResponse, status_code=status.HTTP_200_OK)
async def review_manual_diff(request: ManualReviewRequest) -> ReviewResponse:
    """
    Review a manually provided unified diff using AI agents.
    
    Args:
        request: ManualReviewRequest containing raw diff text
        
    Returns:
        ReviewResponse with comments and summary
        
    Raises:
        HTTPException: If parsing fails or orchestrator errors
    """
    start_time = time.time()
    logger.info("Processing manual diff review request")
    
    try:
        # Parse the diff
        logger.info("Parsing unified diff")
        parsed_files = parse_unified_diff(request.diff)
        
        if not parsed_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid files found in diff"
            )
        
        logger.info(f"Parsed {len(parsed_files)} files, running agents")
        
        # Run agents with timeout
        try:
            comments = await run_orchestrator_with_timeout(parsed_files, timeout=120.0)
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Review timed out. Try with a smaller diff."
            )
        
        logger.info(f"Agents returned {len(comments)} comments")
        
        # Generate summary
        summary = await generate_summary(comments)
        
        # Calculate elapsed time
        elapsed = time.time() - start_time
        logger.info(f"Review completed in {elapsed:.2f}s with {len(comments)} comments")
        
        return ReviewResponse(
            comments=[ReviewComment(**comment) for comment in comments],
            summary=summary
        )
        
    except ValueError as e:
        logger.error(f"Diff parsing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid diff format: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during manual review: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error while processing review: {str(e)}"
        )


@router.post("/github", response_model=ReviewResponse, status_code=status.HTTP_200_OK)
async def review_github_pr(request: GithubReviewRequest) -> ReviewResponse:
    """
    Fetch and review a GitHub pull request using AI agents.
    
    Args:
        request: GithubReviewRequest with owner, repo, and PR number
        
    Returns:
        ReviewResponse with comments and summary
        
    Raises:
        HTTPException: If GitHub API fails, parsing fails, or orchestrator errors
    """
    start_time = time.time()
    logger.info(f"Processing GitHub PR review: {request.owner}/{request.repo}#{request.pr}")
    
    try:
        # Fetch diff from GitHub
        logger.info("Fetching diff from GitHub API")
        diff_text = await fetch_github_pr_diff(request.owner, request.repo, request.pr)
        
        # Parse the diff
        logger.info("Parsing unified diff")
        parsed_files = parse_unified_diff(diff_text)
        
        if not parsed_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid files found in PR diff"
            )
        
        logger.info(f"Parsed {len(parsed_files)} files, running agents")
        
        # Run agents with timeout
        try:
            comments = await run_orchestrator_with_timeout(parsed_files, timeout=120.0)
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Review timed out. The PR may be too large."
            )
        
        logger.info(f"Agents returned {len(comments)} comments")
        
        # Generate summary
        summary = await generate_summary(comments)
        
        # Calculate elapsed time
        elapsed = time.time() - start_time
        logger.info(f"GitHub PR review completed in {elapsed:.2f}s with {len(comments)} comments")
        
        return ReviewResponse(
            comments=[ReviewComment(**comment) for comment in comments],
            summary=summary
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Diff parsing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid diff format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during GitHub PR review: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error while processing GitHub PR: {str(e)}"
        )
