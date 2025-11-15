# Deployment Guide

## Prerequisites

- Python 3.11+
- GitHub Personal Access Token
- OpenAI API Key

## Local Development Setup

### 1. Clone Repository
```powershell
git clone https://github.com/Gnanapreetham2808/Automated-GitHub-Pull-Request-Review-Agent.git
cd "Automated GitHub Pull Request Review Agent"
```

### 2. Create Virtual Environment (Recommended)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment
```powershell
# Copy and edit .env file
cp .env .env.local
notepad .env
```

Add your credentials:
```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxx
```

### 5. Run Development Server
```powershell
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Access:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Production Deployment

### Option 1: Railway

1. Install Railway CLI:
```powershell
npm install -g @railway/cli
```

2. Login and deploy:
```powershell
railway login
railway init
railway up
```

3. Set environment variables in Railway dashboard:
```
GITHUB_TOKEN=your_token
OPENAI_API_KEY=your_key
```

4. Add `railway.json`:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn app:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Option 2: Render

1. Create `render.yaml`:
```yaml
services:
  - type: web
    name: pr-review-agent
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: GITHUB_TOKEN
        sync: false
      - key: OPENAI_API_KEY
        sync: false
```

2. Connect GitHub repo in Render dashboard
3. Add environment variables in Render settings
4. Deploy automatically

### Option 3: Docker

1. Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. Create `.dockerignore`:
```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.git
.gitignore
.env
.vscode
*.log
```

3. Build and run:
```powershell
docker build -t pr-review-agent .
docker run -p 8000:8000 --env-file .env pr-review-agent
```

### Option 4: AWS Lambda + API Gateway

1. Install serverless framework:
```powershell
npm install -g serverless
```

2. Create `serverless.yml`:
```yaml
service: pr-review-agent

provider:
  name: aws
  runtime: python3.11
  stage: prod
  region: us-east-1
  environment:
    GITHUB_TOKEN: ${env:GITHUB_TOKEN}
    OPENAI_API_KEY: ${env:OPENAI_API_KEY}

functions:
  api:
    handler: app.handler
    events:
      - http:
          path: /{proxy+}
          method: ANY
```

3. Add Lambda handler to `app.py`:
```python
from mangum import Mangum
handler = Mangum(app)
```

4. Deploy:
```powershell
serverless deploy
```

### Option 5: Azure App Service

1. Install Azure CLI:
```powershell
winget install Microsoft.AzureCLI
```

2. Login and create app:
```powershell
az login
az webapp up --name pr-review-agent --runtime "PYTHON:3.11"
```

3. Set environment variables:
```powershell
az webapp config appsettings set --name pr-review-agent --settings GITHUB_TOKEN="xxx" OPENAI_API_KEY="xxx"
```

### Option 6: Google Cloud Run

1. Install gcloud CLI

2. Build and deploy:
```powershell
gcloud builds submit --tag gcr.io/PROJECT_ID/pr-review-agent
gcloud run deploy pr-review-agent --image gcr.io/PROJECT_ID/pr-review-agent --platform managed
```

3. Set environment variables in Cloud Run console

## Environment Variables

Required variables for all deployments:

| Variable | Description | Example |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | `ghp_xxxx` |
| `OPENAI_API_KEY` | OpenAI API Key | `sk-xxxx` |
| `PORT` | Server port (auto-set by platforms) | `8000` |

## Health Checks

Configure health check endpoint: `GET /health`

Expected response:
```json
{
  "status": "healthy",
  "service": "PR Review Agent"
}
```

## Monitoring

### Logging
All platforms support log viewing:
- Railway: `railway logs`
- Render: Dashboard logs
- Docker: `docker logs <container>`
- AWS: CloudWatch
- Azure: App Service logs
- GCP: Cloud Logging

### Metrics to Monitor
- Request latency (target: <30s)
- Error rate (target: <1%)
- LLM API failures
- GitHub API rate limits
- Memory usage
- CPU usage

## Scaling

### Horizontal Scaling
Most platforms auto-scale based on traffic:
- Railway: Auto-scales
- Render: Configure in settings
- Docker: Use Docker Swarm or Kubernetes
- Cloud platforms: Auto-scaling groups

### Vertical Scaling
Increase resources for better performance:
- More CPU for concurrent processing
- More memory for larger diffs
- Faster network for API calls

## Security Best Practices

### 1. API Keys
- Never commit `.env` files
- Use platform-specific secret managers
- Rotate keys regularly
- Use separate keys for dev/prod

### 2. Rate Limiting
Add rate limiting middleware:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/review/manual")
@limiter.limit("10/minute")
async def review_manual_diff(request: Request, ...):
    ...
```

### 3. HTTPS
Enable HTTPS on all deployments:
- Most platforms provide free SSL
- Use Let's Encrypt for custom domains
- Enforce HTTPS redirects

### 4. CORS
If building a frontend:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_methods=["POST"],
    allow_headers=["*"],
)
```

## Cost Estimation

### OpenAI API
- gpt-4o-mini: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- Average review: 5-10K tokens
- Cost per review: ~$0.01-0.05

### Platform Costs
- **Railway**: $5/month (Hobby), $20/month (Pro)
- **Render**: Free tier available, $7/month (Starter)
- **AWS Lambda**: Pay per request (~$0.20 per 1M requests)
- **Azure**: ~$13/month (Basic)
- **GCP Cloud Run**: Pay per use (~$0.40 per 1M requests)

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests
        run: pytest tests/
      
      - name: Deploy to Railway
        run: railway up
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## Performance Optimization

### 1. Caching
Add Redis caching for GitHub API responses:
```python
import redis
cache = redis.Redis(host='localhost', port=6379)

async def fetch_github_pr_diff_cached(owner, repo, pr_number):
    cache_key = f"pr:{owner}:{repo}:{pr_number}"
    cached = cache.get(cache_key)
    if cached:
        return cached.decode()
    
    diff = await fetch_github_pr_diff(owner, repo, pr_number)
    cache.setex(cache_key, 3600, diff)  # Cache for 1 hour
    return diff
```

### 2. Connection Pooling
Already implemented with `httpx.AsyncClient`

### 3. Response Compression
```python
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

## Troubleshooting

### Deployment Fails
- Check Python version (3.11+)
- Verify all dependencies in requirements.txt
- Check platform logs for errors

### API Timeouts
- Increase timeout settings on platform
- Optimize LLM calls (reduce max_tokens)
- Implement request queuing

### High Costs
- Reduce LLM temperature
- Implement caching
- Add request limits
- Use cheaper models for simple reviews

## Support

For deployment issues:
1. Check platform documentation
2. Review logs for errors
3. Open GitHub issue
4. Contact platform support

## Next Steps After Deployment

1. ✅ Test all endpoints
2. ✅ Monitor logs and metrics
3. ✅ Set up alerts for errors
4. ✅ Configure auto-scaling
5. ✅ Add custom domain
6. ✅ Implement rate limiting
7. ✅ Set up CI/CD
8. ✅ Document API for team

Your PR Review Agent is now deployed! 🎉
