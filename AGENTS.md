# Agentic Web Search - Agent Guidelines

## Session Initialization — Read This First

**Before starting any work**, scan `main_journal.md` (symlinked in this folder, source at `../main_journal.md`) for cross-project lessons learned. Pay particular attention to entries marked ⭐ CRITICAL.

```bash
cat main_journal.md
```

Key patterns most relevant to this project:
- **docker-compose.yml Port Binding (2026-03-19)** ⭐ CRITICAL — Never use `"PORT:PORT"` shorthand. Always bind to `127.0.0.1:PORT:PORT` for local-only services. The shorthand silently binds to `0.0.0.0`, exposing the service on all interfaces including public ones.
- **Never Hardcode Passwords (2025-12-23)** ⭐ CRITICAL — No credentials in any config or script.
- **Security-First Tool Evaluation (2026-02-06)** — Evaluate blast radius before adding integrations.
- **Design Data Lifecycle Management From Start (2025-12-23)** ⭐ CRITICAL — Plan for data retention and cleanup.

---

## Build/Test Commands
- Install dependencies: `pip install -r requirements.txt`
- Run server: `python src/server.py` (starts HTTP server on port 8000)
- Test endpoints: `curl http://localhost:8000/health` and `curl "http://localhost:8000/search?q=test"`
- Build Docker: `docker compose build`
- Run Docker: `docker compose up -d`
- Stop Docker: `docker compose down`

## Tech Stack
- **Container**: Docker (Ubuntu base)
- **Language**: Python (chosen for mature MCP ecosystem with FastMCP and comprehensive SDK)
- **Purpose**: MCP server for web search capabilities

## Development Guidelines
- Follow MCP (Model Context Protocol) specifications
- Implement web search using DuckDuckGo or Google Search API
- Create "web-search" tool integration for OpenCode
- Use Python with FastMCP framework for MCP server development
- Encapsulate service in Docker container
- Focus on clean API design for search functionality

## Project Structure
Production-ready MCP server with the following components:
- **MCP server implementation** (`src/server.py`) - Full Model Context Protocol compliance with DuckDuckGo search
- **Web search API integration** - DuckDuckGo search with URL extraction
- **OpenCode tool wrapper** - `web_search` tool exposed via MCP protocol
- **Docker configuration** - Containerized deployment with Docker Compose

## Testing
- **Unit tests**: `python -m pytest tests/test_server.py -v`
- **Integration tests**: `python -m pytest tests/test_integration.py -v`
- **Docker deployment**: `docker compose build && docker compose up -d`

## Current Status
MVP is ready to be published.