# MCP Web Search Server

A Model Context Protocol (MCP) server that provides web search capabilities using DuckDuckGo for OpenCode integration.

## Overview

This project implements an MCP server that allows OpenCode to perform web searches. The server uses DuckDuckGo as the search provider and provides both MCP tool integration and a fallback command-line interface for testing.

## Features

- **Web Search**: Perform searches using DuckDuckGo
- **MCP Integration**: Full MCP server implementation with FastMCP
- **Health Checks**: Built-in health monitoring
- **Error Handling**: Comprehensive error handling and logging
- **Docker Support**: Containerized deployment
- **Fallback Mode**: Command-line testing when dependencies are unavailable

## Installation

### Prerequisites

- Python 3.8+
- pip
- Docker (optional)

### Install Dependencies

```bash
pip install -r requirements.txt
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

## Usage

### MCP Server Mode (with FastMCP)

When FastMCP is available, the server runs as a full MCP server:

```bash
python src/server.py
```

### Command-Line Testing Mode

Without FastMCP or when testing:

```bash
# Health check
python src/server.py

# Search query
python src/server.py "your search query here"
```

## API

### Tools

#### `web_search(query: str, max_results: int = 10) -> str`

Performs a web search and returns results in JSON format.

**Parameters:**
- `query`: Search query string
- `max_results`: Maximum number of results (1-50, default: 10)

**Returns:** JSON string with search results

#### `search_health() -> str`

Checks the health status of the search service.

**Returns:** JSON string with health status

### Response Format

Search results:
```json
{
  "query": "search term",
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
  "test_query_successful": true
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
AGENTS.md                # Agent guidelines
project.md               # Project documentation
architecture.md          # Architecture documentation with diagrams
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

### Error Handling

The server gracefully handles:
- Missing dependencies (fallback mode)
- Network errors
- Invalid search queries
- Parsing errors

## Configuration

No configuration files are currently required. The server uses DuckDuckGo's HTML search endpoint with default settings.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.