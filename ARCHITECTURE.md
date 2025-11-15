# System Architecture

## Overview

The Automated PR Review Agent is built with a modular, scalable architecture combining FastAPI for the backend and a multi-agent AI system for intelligent code review.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Client / User                            │
│                (GitHub, API Calls, UI)                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (app.py)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Endpoints:                                           │   │
│  │  • POST /review/manual   - Review raw diff           │   │
│  │  • POST /review/github   - Review GitHub PR          │   │
│  │  • GET  /health          - Health check              │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │  Core Components:                                     │   │
│  │  • Diff Parser - parse_unified_diff()                │   │
│  │  • GitHub API Client - fetch_github_pr_diff()        │   │
│  │  • Request Validation - Pydantic Models              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Multi-Agent System (/agents)                    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Orchestrator (orchestrator.py)                    │     │
│  │  • Coordinates all agents                          │     │
│  │  • Runs agents concurrently (asyncio.gather)       │     │
│  │  • Deduplicates results                            │     │
│  └────────────────────┬───────────────────────────────┘     │
│                       │                                      │
│       ┌───────────────┼───────────────┐                     │
│       │               │               │                     │
│       ▼               ▼               ▼               ▼     │
│  ┌─────────┐   ┌─────────┐   ┌──────────┐   ┌──────────┐  │
│  │ Logic   │   │ Style   │   │ Security │   │Performance│  │
│  │ Agent   │   │ Agent   │   │ Agent    │   │ Agent    │  │
│  └────┬────┘   └────┬────┘   └────┬─────┘   └────┬─────┘  │
│       │             │              │              │         │
│       └─────────────┴──────────────┴──────────────┘         │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Base Agent (base_agent.py)                          │   │
│  │  • Abstract interface                                │   │
│  │  • _format_output() - Parse LLM responses           │   │
│  │  • _fallback_parse() - Handle invalid JSON          │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
└─────────────────────────┼────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              LLM Client (llm_client.py)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  • Async OpenAI API calls                            │   │
│  │  • Retry logic with exponential backoff              │   │
│  │  • Timeout handling                                  │   │
│  │  • Rate limit management                             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   OpenAI API (GPT-4o-mini)                   │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Manual Diff Review Flow

```
User Request (diff text)
    │
    ▼
FastAPI Endpoint (/review/manual)
    │
    ▼
parse_unified_diff()
    │ (parsed files with hunks)
    ▼
Orchestrator.run_agents_on_files()
    │
    ├─► LogicAgent.review()
    │       │
    │       ├─► _extract_hunk_snippet()
    │       ├─► llm_call() → OpenAI API
    │       └─► _format_output()
    │
    ├─► StyleAgent.review()
    │       └─► (same pattern)
    │
    ├─► SecurityAgent.review()
    │       └─► (same pattern)
    │
    └─► PerformanceAgent.review()
            └─► (same pattern)
    │
    ▼
Aggregate & Deduplicate Results
    │
    ▼
AgentReviewResponse
    │
    ▼
Return JSON to User
```

### 2. GitHub PR Review Flow

```
User Request (owner, repo, pr#)
    │
    ▼
FastAPI Endpoint (/review/github)
    │
    ▼
fetch_github_pr_diff()
    │ (GitHub API call)
    ▼
parse_unified_diff()
    │
    ▼
[Same agent flow as manual review]
    │
    ▼
Return JSON to User
```

## Component Details

### FastAPI Backend (`app.py`)
- **Purpose**: HTTP API layer and diff parsing
- **Key Functions**:
  - `parse_unified_diff()`: Parses git unified diff format
  - `fetch_github_pr_diff()`: Fetches PR from GitHub API
  - Endpoint handlers with validation

### LLM Client (`llm_client.py`)
- **Purpose**: Abstraction layer for OpenAI API
- **Features**:
  - Async/await support
  - Automatic retry (3 attempts)
  - Exponential backoff
  - Error classification

### Base Agent (`base_agent.py`)
- **Purpose**: Abstract class defining agent interface
- **Key Methods**:
  - `review()`: Abstract method for agent implementation
  - `_format_output()`: Parse JSON responses
  - `_fallback_parse()`: Handle malformed responses
  - `_extract_hunk_snippet()`: Prepare code snippets

### Specialized Agents
Each agent inherits from `BaseAgent` and implements:
- `SYSTEM_PROMPT`: Specialized instructions for LLM
- `review()`: Analysis logic for specific domain

| Agent | Focus Area | Key Detections |
|-------|-----------|----------------|
| **LogicAgent** | Correctness | Off-by-one, null refs, edge cases |
| **StyleAgent** | Maintainability | Naming, complexity, documentation |
| **SecurityAgent** | Vulnerabilities | Injections, secrets, auth issues |
| **PerformanceAgent** | Efficiency | N+1 queries, algorithm issues |

### Orchestrator (`orchestrator.py`)
- **Purpose**: Coordinate agent execution
- **Features**:
  - Concurrent agent execution (`asyncio.gather`)
  - Result aggregation
  - Deduplication by path + body prefix
  - Error isolation (one agent failure doesn't stop others)

## Technology Stack

- **Framework**: FastAPI 0.109.0
- **LLM**: OpenAI GPT-4o-mini
- **HTTP Client**: httpx (async)
- **Validation**: Pydantic 2.5.3
- **Server**: Uvicorn
- **Language**: Python 3.11+

## Scalability Considerations

### Current Architecture
- Single-server deployment
- Synchronous processing per request
- In-memory result handling

### Future Enhancements
- **Queue System**: Add Celery/Redis for background processing
- **Caching**: Cache GitHub API responses
- **Database**: Store review history
- **Rate Limiting**: Protect API endpoints
- **Load Balancing**: Multiple server instances
- **Webhooks**: Auto-review on PR creation

## Security Architecture

### API Key Management
- Environment variables for secrets
- Never logged or exposed in responses
- Separate dev/prod configurations

### Input Validation
- Pydantic models validate all inputs
- Diff size limits (prevent abuse)
- GitHub API rate limit handling

### Output Sanitization
- LLM responses parsed and validated
- Fallback for malformed responses
- No code execution from LLM output

## Error Handling Strategy

```
Request → Validation → Processing → LLM Calls → Response
   ↓          ↓            ↓           ↓           ↓
  400        400          500         Retry       200
(Bad Input) (Invalid)   (Server)  (3 attempts)  (Success)
                                       ↓
                                   Log + Continue
                                   (Don't fail entire request)
```

## Monitoring & Logging

- **Levels**: INFO, DEBUG, WARNING, ERROR
- **Logged Events**:
  - API requests/responses
  - Agent execution status
  - LLM call attempts
  - Errors and exceptions

## Configuration

### Environment Variables
```env
GITHUB_TOKEN=ghp_xxx      # GitHub API access
OPENAI_API_KEY=sk-xxx     # OpenAI API access
```

### Tunable Parameters
- `max_retries`: LLM retry attempts (default: 3)
- `timeout`: LLM request timeout (default: 30s)
- `temperature`: LLM creativity (default: 0.3)
- `max_tokens`: LLM response length (default: 2000)
- `max_lines`: Hunk snippet size (default: 60)

## Performance Metrics

### Typical Request Times
- Diff parsing: ~50-200ms
- GitHub API fetch: ~500-2000ms
- Single agent review: ~2-5s per hunk
- Total review (4 agents): ~3-10s per file

### Optimization Strategies
- Concurrent agent execution (4x speedup)
- Snippet truncation (reduce tokens)
- Result caching (future)
- Batch processing (future)
