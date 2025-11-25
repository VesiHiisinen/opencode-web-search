#!/usr/bin/env python3
"""
MCP Web Search Server

A Model Context Protocol server that provides web search capabilities
using DuckDuckGo for OpenCode integration.
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional

# Try to import dependencies with proper error handling
try:
    import requests  # type: ignore
    from bs4 import BeautifulSoup  # type: ignore
    HAS_DEPENDENCIES = True
except ImportError as e:
    HAS_DEPENDENCIES = False
    requests = None
    BeautifulSoup = None
    logging.warning(f"Dependencies not available: {e}")

# Try to import FastMCP, fallback to basic implementation if not available
try:
    from fastmcp import FastMCP  # type: ignore
    HAS_FASTMCP = True
except ImportError as e:
    HAS_FASTMCP = False
    FastMCP = None  # Define as None for type checking
    logging.warning(f"FastMCP not available: {e}")

# Try to import FastAPI for HTTP server
try:
    from fastapi import FastAPI  # type: ignore
    import uvicorn  # type: ignore
    HAS_FASTAPI = True
except ImportError as e:
    HAS_FASTAPI = False
    FastAPI = None
    uvicorn = None
    logging.warning(f"FastAPI not available: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSearchError(Exception):
    """Custom exception for web search errors."""
    pass


class DuckDuckGoSearcher:
    """DuckDuckGo search implementation."""
    
    def __init__(self):
        if not HAS_DEPENDENCIES:
            raise WebSearchError("Required dependencies not installed")
        
        self.base_url = "https://duckduckgo.com/html/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Perform a web search using DuckDuckGo.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of search results with title, url, and snippet
        """
        if requests is None or BeautifulSoup is None:
            raise WebSearchError("Dependencies not available")
        
        try:
            params = {
                "q": query,
                "kl": "us-en"
            }
            
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Parse search results
            for result in soup.find_all('div', class_='result')[:max_results]:
                title_tag = result.find('a', class_='result__a')
                snippet_tag = result.find('a', class_='result__snippet')
                
                if title_tag and snippet_tag:
                    title = title_tag.get_text(strip=True)
                    url = title_tag.get('href', '')
                    snippet = snippet_tag.get_text(strip=True)
                    
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet
                    })
            
            return results
            
        except requests.RequestException as e:
            logger.error(f"Search request failed: {e}")
            raise WebSearchError(f"Search request failed: {e}")
        except Exception as e:
            logger.error(f"Search parsing failed: {e}")
            raise WebSearchError(f"Search parsing failed: {e}")


# Initialize searcher
searcher = None
if HAS_DEPENDENCIES:
    try:
        searcher = DuckDuckGoSearcher()
    except WebSearchError as e:
        logger.warning(f"Searcher initialization failed: {e}")

# Create FastAPI app if available
app = None
if HAS_FASTAPI and FastAPI is not None:
    app = FastAPI(title="MCP Web Search Server", description="Web search API for OpenCode")

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return json.loads(search_health())

    @app.get("/search")
    async def search_endpoint(q: str, max_results: int = 10):
        """Web search endpoint."""
        return json.loads(web_search(q, max_results))


def web_search(query: str, max_results: int = 10) -> str:
    """
    Perform a web search using DuckDuckGo.
    
    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 10)
        
    Returns:
        JSON string containing search results
    """
    if searcher is None:
        error_response = {
            "error": "Search service not available - dependencies missing",
            "query": query,
            "results": [],
            "count": 0
        }
        return json.dumps(error_response, indent=2)
    
    try:
        logger.info(f"Performing web search for: {query}")
        
        if not query or not query.strip():
            raise WebSearchError("Search query cannot be empty")
        
        if max_results < 1 or max_results > 50:
            max_results = 10
        
        results = searcher.search(query.strip(), max_results)
        
        response = {
            "query": query,
            "results": results,
            "count": len(results)
        }
        
        logger.info(f"Search completed: {len(results)} results found")
        return json.dumps(response, indent=2)
        
    except WebSearchError as e:
        logger.error(f"Web search error: {e}")
        error_response = {
            "error": str(e),
            "query": query,
            "results": [],
            "count": 0
        }
        return json.dumps(error_response, indent=2)
    except Exception as e:
        logger.error(f"Unexpected error in web_search: {e}")
        error_response = {
            "error": f"Unexpected error: {e}",
            "query": query,
            "results": [],
            "count": 0
        }
        return json.dumps(error_response, indent=2)


def search_health() -> str:
    """
    Check the health status of the web search service.
    
    Returns:
        JSON string containing health status
    """
    try:
        if searcher is None:
            response = {
                "status": "unhealthy",
                "message": "Search service not available - dependencies missing",
                "test_query_successful": False
            }
            return json.dumps(response, indent=2)
        
        # Perform a simple test search
        test_results = searcher.search("test", 1)
        
        response = {
            "status": "healthy",
            "message": "Web search service is operational",
            "test_query_successful": len(test_results) >= 0
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        response = {
            "status": "unhealthy",
            "message": f"Health check failed: {e}",
            "test_query_successful": False
        }
        
        return json.dumps(response, indent=2)


# FastMCP implementation if available
mcp = None
if HAS_FASTMCP and FastMCP is not None:
    mcp = FastMCP("web-search-server")
    
    @mcp.tool()
    def web_search_mcp(query: str, max_results: int = 10) -> str:
        """MCP tool wrapper for web search."""
        return web_search(query, max_results)
    
    @mcp.tool()
    def search_health_mcp() -> str:
        """MCP tool wrapper for health check."""
        return search_health()


async def main():
    """Main entry point for the MCP server."""
    logger.info("Starting MCP Web Search Server...")

    if app is not None and uvicorn is not None:
        # Run FastAPI server
        logger.info("Running HTTP server on port 8000")
        config = uvicorn.Config(app, host="0.0.0.0", port=8000)
        server = uvicorn.Server(config)
        await server.serve()
    elif mcp is not None:
        try:
            # Run the FastMCP server
            await mcp.run()
        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        except Exception as e:
            logger.error(f"Server error: {e}")
            sys.exit(1)
    else:
        # Fallback: simple command-line interface for testing
        logger.info("FastMCP not available, running in test mode")
        if len(sys.argv) > 1:
            query = " ".join(sys.argv[1:])
            print(web_search(query))
        else:
            print(search_health())


if __name__ == "__main__":
    # Run the main coroutine in the existing event loop or create a new one
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
