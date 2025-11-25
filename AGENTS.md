# Agentic Web Search - Agent Guidelines

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
Currently in planning phase. Core components will include:
- MCP server implementation
- Web search API integration
- OpenCode tool wrapper
- Docker configuration

Note: This project is expanding OpenCode with web search capabilities.