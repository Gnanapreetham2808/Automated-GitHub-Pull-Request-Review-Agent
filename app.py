"""
Automated Pull Request Review Agent - Core Backend
FastAPI application for processing and parsing GitHub pull request diffs.
"""

import logging

from fastapi import FastAPI

from routes.review import router as review_router

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

# Include routers
app.include_router(review_router)


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
