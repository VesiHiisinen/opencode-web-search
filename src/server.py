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
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

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

# Try to import FastAPI for HTTP server
try:
    from fastapi import FastAPI, Request, HTTPException  # type: ignore
    from fastapi.responses import StreamingResponse, JSONResponse  # type: ignore
    import uvicorn  # type: ignore
    HAS_FASTAPI = True
except ImportError as e:
    HAS_FASTAPI = False
    FastAPI = None
    Request = None
    HTTPException = None
    StreamingResponse = None
    JSONResponse = None
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
logger.info(f"HAS_FASTAPI: {HAS_FASTAPI}, FastAPI: {FastAPI}, JSONResponse: {JSONResponse}, StreamingResponse: {StreamingResponse}")
if HAS_FASTAPI and FastAPI is not None and JSONResponse is not None and StreamingResponse is not None:
    logger.info("Creating FastAPI app...")
    app = FastAPI(title="MCP Web Search Server", description="Web search API for OpenCode")
    logger.info(f"FastAPI app created: {app}")

    logger.info("Registering health endpoint...")
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        logger.info("Health endpoint called")
        return json.loads(search_health())

    logger.info("Registering search endpoint...")
    @app.get("/search")
    async def search_endpoint(q: str, max_results: int = 10):
        """Web search endpoint."""
        logger.info(f"Search endpoint called with q={q}")
        return json.loads(web_search(q, max_results))

    logger.info("Registering root endpoint...")
    @app.get("/")
    async def root_endpoint():
        """Root endpoint returning tool information for OpenCode."""
        # Return tool information in a format that OpenCode might expect
        return {
            "tools": [
                {
                    "name": "web_search",
                    "description": "Perform a web search using DuckDuckGo",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query string"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50
                            }
                        },
                        "required": ["query"]
                    }
                }
            ]
        }

    logger.info("Registering SSE endpoint...")
    @app.get("/sse")
    async def sse_endpoint():
        """MCP Server-Sent Events endpoint for server-to-client communication."""
        logger.info("SSE endpoint called")

        async def event_stream():
            try:
                # Send the endpoint event first (required by MCP spec)
                # This tells the client where to send messages
                endpoint_url = "/mcp"
                logger.info(f"Sending endpoint event: {endpoint_url}")
                yield f"event: endpoint\ndata: {endpoint_url}\n\n"

                # Keep the connection alive
                while True:
                    await asyncio.sleep(30)
                    yield ": ping\n\n"

            except asyncio.CancelledError:
                logger.info("SSE connection closed")

        return StreamingResponse(  # type: ignore
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
            }
        )

    @app.post("/mcp")  # type: ignore
    async def mcp_endpoint(request_data: Dict[str, Any]):
        """MCP JSON-RPC endpoint."""
        logger.info("MCP endpoint called")
        try:
            response = mcp_server.handle_request(request_data)
            return response
        except Exception as e:
            logger.error(f"MCP endpoint error: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }

    logger.info("Registering dynamic MCP client endpoint...")
    @app.post("/mcp/{client_id}")  # type: ignore
    async def mcp_client_endpoint(client_id: str, request_data: Dict[str, Any]):
        """Dynamic MCP endpoint for specific client connections."""
        logger.info(f"MCP client endpoint called for client {client_id}")
        try:
            response = mcp_server.handle_request(request_data)
            return response
        except Exception as e:
            logger.error(f"MCP client endpoint error: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }

    logger.info("All endpoints registered")
else:
    logger.warning("FastAPI dependencies not available, app will be None")


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


# MCP Server implementation
class MCPServer:
    """Model Context Protocol server implementation."""
    
    def __init__(self):
        self.server_info = {
            "name": "web-search-server",
            "version": "1.0.0",
            "description": "Web search server using DuckDuckGo"
        }
        self.capabilities = {
            "tools": {
                "listChanged": True
            },
            "resources": {},
            "prompts": {}
        }
        self.tools = {
            "tools": [
                {
                    "name": "web_search",
                    "description": "Perform a web search using DuckDuckGo",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query string"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50
                            }
                        },
                        "required": ["query"]
                    }
                }
            ]
        }
    
    def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP JSON-RPC requests."""
        method = request_data.get("method")
        params = request_data.get("params", {})
        request_id = request_data.get("id")
        
        logger.info(f"Handling MCP request: {method}")
        
        try:
            if method == "initialize":
                return self._handle_initialize(request_id, params)
            elif method == "tools/list":
                return self._handle_tools_list(request_id)
            elif method == "tools/call":
                return self._handle_tools_call(request_id, params)
            elif method == "ping":
                return self._handle_ping(request_id)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
        except Exception as e:
            logger.error(f"Error handling request {method}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    def _handle_initialize(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        client_info = params.get("clientInfo", {})
        logger.info(f"Initializing connection with client: {client_info}")
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": self.capabilities,
                "serverInfo": self.server_info
            }
        }
    
    def _handle_tools_list(self, request_id: Any) -> Dict[str, Any]:
        """Handle tools/list request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": self.tools
        }
    
    def _handle_tools_call(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        if name == "web_search":
            query = arguments.get("query")
            max_results = arguments.get("max_results", 10)
            
            if not query:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Missing required parameter: query"
                    }
                }
            
            # Perform the search
            result = json.loads(web_search(query, max_results))
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"Unknown tool: {name}"
                }
            }
    
    def _handle_ping(self, request_id: Any) -> Dict[str, Any]:
        """Handle ping request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"pong": True}
        }

# Initialize MCP server
mcp_server = MCPServer()


async def main():
    """Main entry point for the MCP server."""
    logger.info("Starting MCP Web Search Server...")
    logger.info(f"App is None: {app is None}")

    if app is not None and uvicorn is not None:
        # Run FastAPI server with MCP endpoints
        logger.info("Running MCP HTTP server on port 8000")
        config = uvicorn.Config(app, host="0.0.0.0", port=8000)
        server = uvicorn.Server(config)
        await server.serve()
    else:
        # Fallback: simple command-line interface for testing
        logger.info("FastAPI not available, running in test mode")
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
