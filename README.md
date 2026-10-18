# MCP Web Search Server

A Model Context Protocol (MCP) server that provides web search capabilities using DuckDuckGo and Google PSE (Programmable Search Engine) for OpenCode integration.

## Overview

This project implements an MCP server that allows OpenCode to perform web searches. The server supports two search providers:

- **DuckDuckGo**: Free, no authentication required, up to 50 results
- **Google PSE**: Requires API credentials, up to 10 results, 100 queries/day free tier

The server uses FastMCP with Streamable HTTP transport for compatibility with modern MCP clients (protocol version 2025-03-26).

## Features

- **Dual Search Providers**: DuckDuckGo and Google PSE with automatic provider selection
- **MCP Integration**: Full MCP server implementation with FastMCP
- **Streamable HTTP Transport**: Modern MCP protocol compliance
- **Health Checks**: Built-in health endpoint for all providers
- **Error Handling**: Comprehensive error handling and logging
- **Docker Support**: Containerized deployment with environment variable support
- **Fallback Support**: Optional automatic fallback to alternate provider on failure

## Installation

### Prerequisites

- Python 3.8+
- pip
- Docker (optional)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### OpenCode Configuration

To integrate this MCP server with OpenCode, add the following to your `~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "websearch": {
      "type": "remote",
      "url": "http://127.0.0.1:8000",
      "enabled": true
    }
  }
}
```

### Docker Installation

Using Docker Compose (recommended):

```bash
docker compose build
docker compose up -d
```

Or manually:

```bash
docker build -t web-search-server .
docker run -p 127.0.0.1:8000:8000 web-search-server
```

## Configuration

### Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```bash
# Google PSE Credentials (optional, only needed for Google provider)
GOOGLE_PSE_API_KEY=your_api_key_here
GOOGLE_PSE_ENGINE_ID=your_engine_id_here

# Optional: Default provider (duckduckgo or google)
DEFAULT_SEARCH_PROVIDER=duckduckgo

# Optional: Enable automatic fallback on provider failure
ENABLE_FALLBACK=false
```

**Note**: DuckDuckGo requires no credentials. Google PSE requires both `GOOGLE_PSE_API_KEY` and `GOOGLE_PSE_ENGINE_ID`.

## OpenCode Integration

To use this MCP server with OpenCode, add the following configuration to your `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "web-search": {
      "type": "remote",
      "url": "http://localhost:8000",
      "enabled": true
    }
  }
}
```

This enables the `web_search` tool in OpenCode for performing web searches.

## Usage

### Running the Server

```bash
python src/server.py
```

The server starts on port 8000 and provides:
- MCP endpoint for tool invocations
- Health check endpoint at `/health`

### Health Check

```bash
curl http://localhost:8000/health
```

## API

### Tools

#### `web_search(query: str, max_results: int = 10, provider: str = "auto") -> str`

Performs a web search and returns results in JSON format.

**Parameters:**
- `query`: Search query string
- `max_results`: Maximum number of results (1-50, default: 10)
- `provider`: Search provider to use:
  - `"auto"`: Use default provider (env-configurable, default: duckduckgo)
  - `"duckduckgo"`: Use DuckDuckGo (50 results max, no auth required)
  - `"google"`: Use Google PSE (10 results max, requires API credentials)

**Returns:** JSON string with search results

#### `search_health() -> str`

Checks the health status of the search service.

**Returns:** JSON string with health status for all configured providers

### Response Format

Search results:
```json
{
  "query": "search term",
  "provider": "duckduckgo",
  "results": [
    {
      "title": "Result Title",
      "url": "https://example.com",
      "snippet": "Result description..."
    }
  ],
  "count": 1
}
```

Health check:
```json
{
  "status": "healthy",
  "message": "Web search service is operational",
  "providers": {
    "duckduckgo": {
      "status": "healthy",
      "max_results": 50
    }
  }
}
```

## Development

### Project Structure

```
src/
├── __init__.py
└── server.py            # Main MCP server implementation
tests/
├── test_server.py       # Unit tests
└── test_integration.py  # Integration/E2E tests
requirements.txt         # Python dependencies
Dockerfile               # Docker configuration
docker-compose.yml       # Docker Compose configuration
.env.example             # Environment variable template
AGENTS.md                # Agent guidelines
project.md               # Project documentation
architecture.md          # Architecture documentation with diagrams
GOOGLE_PSE_IMPLEMENTATION_PLAN.md  # Implementation details
```

### Testing

Run unit tests:

```bash
python -m pytest tests/test_server.py -v
```

Run integration tests (requires server running):

```bash
docker compose up -d
python -m pytest tests/test_integration.py -v
```

Run all tests:

```bash
python -m pytest tests/ -v
```

### Provider Limits

| Provider | Max Results | Authentication | Notes |
|----------|-------------|----------------|-------|
| DuckDuckGo | 50 | None | Be respectful with rate |
| Google PSE | 10 | API Key + Engine ID | 100 queries/day free tier |

### Error Handling

The server gracefully handles:
- Missing dependencies (fallback mode)
- Network errors
- Invalid search queries
- Parsing errors
- Missing provider credentials
- API quota exceeded

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
