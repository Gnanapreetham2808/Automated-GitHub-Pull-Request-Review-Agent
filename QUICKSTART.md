# Quick Start Guide

## Step 1: Install Dependencies

```powershell
pip install -r requirements.txt
```

## Step 2: Configure Environment

Edit the `.env` file and add your API keys:

```env
GITHUB_TOKEN=ghp_your_github_token_here
OPENAI_API_KEY=sk-your_openai_key_here
```

### Getting API Keys

**GitHub Token:**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo` (for private) or `public_repo` (for public only)
4. Copy the token

**OpenAI API Key:**
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key

## Step 3: Run the Server

```powershell
uvicorn app:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

## Step 4: Test the API

### Option 1: Use the Interactive Docs

Open your browser: http://localhost:8000/docs

Try the `/review/manual` endpoint with this sample diff:

```json
{
  "diff": "diff --git a/test.py b/test.py\nindex 123..456 100644\n--- a/test.py\n+++ b/test.py\n@@ -1,3 +1,4 @@\n def example():\n-    pass\n+    x = 1\n+    return x"
}
```

### Option 2: Use the Example Script

```powershell
python example_usage.py
```

### Option 3: Use cURL

```powershell
curl -X POST "http://localhost:8000/review/manual" `
  -H "Content-Type: application/json" `
  -d '{"diff": "diff --git a/test.py..."}'
```

## Step 5: Review a Real GitHub PR

```powershell
# Using PowerShell
$body = @{
    owner = "facebook"
    repo = "react"
    pr = 12345
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/review/github" `
  -ContentType "application/json" -Body $body
```

## Troubleshooting

### "GITHUB_TOKEN not configured"
- Make sure `.env` file exists
- Check that GITHUB_TOKEN is set correctly
- No quotes around the token value

### "OPENAI_API_KEY not set"
- Add OPENAI_API_KEY to `.env` file
- Verify you have API credits at https://platform.openai.com/usage

### "Module not found"
- Run `pip install -r requirements.txt`
- Make sure you're in the correct directory

### "Port already in use"
- Change port: `uvicorn app:app --reload --port 8001`
- Or kill the process using port 8000

## Next Steps

1. **Customize Agents**: Edit system prompts in `/agents/*_agent.py`
2. **Add New Agents**: Create new agent files following the `BaseAgent` pattern
3. **Adjust Settings**: Modify temperature, max_tokens in `llm_client.py`
4. **Deploy**: Use Docker or cloud platforms (Railway, Render, etc.)

## API Examples

### Review a Manual Diff
```python
import requests

response = requests.post(
    "http://localhost:8000/review/manual",
    json={"diff": "your diff here"}
)
print(response.json())
```

### Review a GitHub PR
```python
import requests

response = requests.post(
    "http://localhost:8000/review/github",
    json={
        "owner": "username",
        "repo": "repository",
        "pr": 42
    }
)
print(response.json())
```

## Support

For issues or questions:
- Check logs in the terminal where uvicorn is running
- Review the API docs at http://localhost:8000/docs
- Open an issue on GitHub
