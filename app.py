"""
Automated Pull Request Review Agent - Core Backend
FastAPI application for processing and parsing GitHub pull request diffs.
"""

import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request

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

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(review_router)


# ==================== API Endpoints ====================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the frontend UI."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api")
async def api_info():
    """API information endpoint."""
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
