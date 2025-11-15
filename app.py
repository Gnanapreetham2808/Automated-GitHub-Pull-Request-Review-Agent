"""
Automated Pull Request Review Agent - Core Backend
FastAPI application for processing and parsing GitHub pull request diffs.
"""

import logging
import os
import re
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, validator

from agents.orchestrator import run_agents_on_files

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PR Review Agent",
    description="Automated Pull Request Review Agent for parsing and analyzing PR diffs",
    version="1.0.0"
)


# ==================== Pydantic Models ====================

class ManualDiffRequest(BaseModel):
    """Request model for manual diff review endpoint."""
    diff: str = Field(..., min_length=1, description="Raw unified diff text")

    @validator("diff")
    def validate_diff_not_empty(cls, v: str) -> str:
        """Validate that diff is not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Diff cannot be empty or whitespace only")
        return v


class GitHubPRRequest(BaseModel):
    """Request model for GitHub PR review endpoint."""
    owner: str = Field(..., min_length=1, description="GitHub repository owner")
    repo: str = Field(..., min_length=1, description="GitHub repository name")
    pr: int = Field(..., gt=0, description="Pull request number")

    @validator("owner", "repo")
    def validate_not_empty(cls, v: str) -> str:
        """Validate that owner and repo are not empty."""
        if not v or not v.strip():
            raise ValueError("Owner and repo cannot be empty")
        return v.strip()


class DiffHunk(BaseModel):
    """Model representing a single hunk in a diff."""
    header: str = Field(..., description="Hunk header (e.g., @@ -10,0 +11,5 @@)")
    lines: List[str] = Field(..., description="List of changed lines with prefixes (+, -, or space)")


class ParsedFile(BaseModel):
    """Model representing a parsed file from diff."""
    path: str = Field(..., description="File path")
    hunks: List[DiffHunk] = Field(..., description="List of hunks in the file")


class DiffParseResponse(BaseModel):
    """Response model for diff parsing."""
    files: List[ParsedFile] = Field(..., description="List of parsed files with their changes")
    total_files: int = Field(..., description="Total number of files changed")
    total_hunks: int = Field(..., description="Total number of hunks across all files")


class AgentReviewComment(BaseModel):
    """Model for agent-generated review comments."""
    path: str = Field(..., description="File path")
    line: int = Field(..., description="Line number")
    side: str = Field(..., description="Side of diff: 'new' or 'old'")
    category: str = Field(..., description="Review category (logic, style, security, performance)")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)")
    body: str = Field(..., description="Review comment text")


class AgentReviewResponse(BaseModel):
    """Response model for agent review."""
    comments: List[AgentReviewComment] = Field(..., description="List of review comments")
    total_comments: int = Field(..., description="Total number of comments")
    files_reviewed: int = Field(..., description="Number of files reviewed")


# ==================== Core Diff Parser ====================

def parse_unified_diff(diff: str) -> List[ParsedFile]:
    """
    Parse a unified diff string into structured format.
    
    Args:
        diff: Raw unified diff text
        
    Returns:
        List of ParsedFile objects containing file paths and their hunks
        
    Raises:
        ValueError: If diff is empty or invalid
    """
    if not diff or not diff.strip():
        raise ValueError("Diff cannot be empty")
    
    files: List[ParsedFile] = []
    lines = diff.split("\n")
    
    current_file: Optional[str] = None
    current_hunks: List[DiffHunk] = []
    current_hunk_header: Optional[str] = None
    current_hunk_lines: List[str] = []
    
    def save_current_hunk() -> None:
        """Helper to save the current hunk being processed."""
        if current_hunk_header is not None and current_hunk_lines:
            current_hunks.append(DiffHunk(
                header=current_hunk_header,
                lines=current_hunk_lines.copy()
            ))
    
    def save_current_file() -> None:
        """Helper to save the current file being processed."""
        if current_file is not None and current_hunks:
            files.append(ParsedFile(
                path=current_file,
                hunks=current_hunks.copy()
            ))
    
    for line in lines:
        # Check for file header (diff --git a/... b/...)
        if line.startswith("diff --git"):
            # Save previous file if exists
            save_current_hunk()
            save_current_file()
            
            # Reset for new file
            current_file = None
            current_hunks = []
            current_hunk_header = None
            current_hunk_lines = []
            
        # Extract file path from +++ b/...
        elif line.startswith("+++ b/"):
            current_file = line[6:]  # Remove "+++ b/" prefix
            
        # Extract file path from +++ (for new files)
        elif line.startswith("+++ /dev/null"):
            # File was deleted, keep previous path from ---
            pass
            
        # Extract file path from --- a/... (fallback)
        elif line.startswith("--- a/") and current_file is None:
            current_file = line[6:]  # Remove "--- a/" prefix
            
        # Check for hunk header (@@ ... @@)
        elif line.startswith("@@"):
            # Save previous hunk if exists
            save_current_hunk()
            
            # Extract hunk header
            match = re.match(r"^(@@[^@]+@@)", line)
            if match:
                current_hunk_header = match.group(1)
                current_hunk_lines = []
            
        # Process hunk content lines
        elif current_hunk_header is not None:
            # Lines starting with +, -, or space are part of the hunk
            if line.startswith(("+", "-", " ")):
                current_hunk_lines.append(line)
            # Context lines (no prefix in some cases)
            elif line and not line.startswith("\\"):  # Ignore "\ No newline at end of file"
                # If we're in a hunk and line doesn't start with special char,
                # treat as context (add space prefix)
                if current_hunk_lines:  # Only if we have started collecting lines
                    current_hunk_lines.append(f" {line}")
    
    # Save last hunk and file
    save_current_hunk()
    save_current_file()
    
    logger.info(f"Parsed {len(files)} files from diff")
    return files


# ==================== Helper Functions ====================

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
            # First, get PR metadata to get diff_url
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
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"GitHub API error: {response.status_code} - {response.text}"
                )
            
            pr_data = response.json()
            diff_url = pr_data.get("diff_url")
            
            if not diff_url:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="diff_url not found in PR response"
                )
            
            # Fetch the actual diff
            logger.info(f"Fetching diff from: {diff_url}")
            diff_response = await client.get(diff_url, headers=headers)
            
            if diff_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to GitHub API: {str(e)}"
        )


# ==================== API Endpoints ====================

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "PR Review Agent",
        "version": "1.0.0",
        "endpoints": {
            "manual_review": "/review/manual",
            "github_review": "/review/github"
        }
    }


@app.post("/review/manual", response_model=AgentReviewResponse, status_code=status.HTTP_200_OK)
async def review_manual_diff(request: ManualDiffRequest) -> AgentReviewResponse:
    """
    Parse a manually provided unified diff and run AI agents for review.
    
    Args:
        request: ManualDiffRequest containing raw diff text
        
    Returns:
        AgentReviewResponse with AI-generated review comments
        
    Raises:
        HTTPException: If diff is invalid or parsing fails
    """
    logger.info("Processing manual diff review request with AI agents")
    
    try:
        parsed_files = parse_unified_diff(request.diff)
        
        if not parsed_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid files found in diff"
            )
        
        logger.info(f"Parsed {len(parsed_files)} files, running AI agents...")
        
        # Convert to dict format for agents
        files_for_agents = [
            {
                "path": file.path,
                "hunks": [
                    {"header": hunk.header, "lines": hunk.lines}
                    for hunk in file.hunks
                ]
            }
            for file in parsed_files
        ]
        
        # Run agents
        comments = await run_agents_on_files(files_for_agents)
        
        logger.info(f"AI review complete: {len(comments)} comments generated")
        
        return AgentReviewResponse(
            comments=[AgentReviewComment(**comment) for comment in comments],
            total_comments=len(comments),
            files_reviewed=len(parsed_files)
        )
        
    except ValueError as e:
        logger.error(f"Diff parsing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid diff format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during diff parsing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error while processing review: {str(e)}"
        )


@app.post("/review/github", response_model=AgentReviewResponse, status_code=status.HTTP_200_OK)
async def review_github_pr(request: GitHubPRRequest) -> AgentReviewResponse:
    """
    Fetch and parse a GitHub pull request diff, then run AI agents for review.
    
    Args:
        request: GitHubPRRequest with owner, repo, and PR number
        
    Returns:
        AgentReviewResponse with AI-generated review comments
        
    Raises:
        HTTPException: If GitHub API fails or diff parsing fails
    """
    logger.info(f"Processing GitHub PR review with AI agents: {request.owner}/{request.repo}#{request.pr}")
    
    try:
        # Fetch diff from GitHub
        diff_text = await fetch_github_pr_diff(request.owner, request.repo, request.pr)
        
        # Parse the diff
        parsed_files = parse_unified_diff(diff_text)
        
        if not parsed_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid files found in PR diff"
            )
        
        logger.info(f"Parsed PR {request.pr}: {len(parsed_files)} files, running AI agents...")
        
        # Convert to dict format for agents
        files_for_agents = [
            {
                "path": file.path,
                "hunks": [
                    {"header": hunk.header, "lines": hunk.lines}
                    for hunk in file.hunks
                ]
            }
            for file in parsed_files
        ]
        
        # Run agents
        comments = await run_agents_on_files(files_for_agents)
        
        logger.info(f"AI review complete for PR {request.pr}: {len(comments)} comments generated")
        
        return AgentReviewResponse(
            comments=[AgentReviewComment(**comment) for comment in comments],
            total_comments=len(comments),
            files_reviewed=len(parsed_files)
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (already logged in fetch function)
        raise
    except ValueError as e:
        logger.error(f"Diff parsing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid diff format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during GitHub PR processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error while processing GitHub PR: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "PR Review Agent"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
