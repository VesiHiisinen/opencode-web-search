#!/usr/bin/env python3
"""
MCP Web Search Server

A Model Context Protocol server that provides web search capabilities
using DuckDuckGo and Google PSE (Programmable Search Engine) for OpenCode integration.

Uses FastMCP with Streamable HTTP transport for compatibility with
modern MCP clients (protocol version 2025-03-26).
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import parse_qs, urlparse, unquote

import requests
from bs4 import BeautifulSoup
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSearchError(Exception):
    """Custom exception for web search errors."""
    pass


class BaseSearchProvider(ABC):
    """Abstract base class for search providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'duckduckgo', 'google')."""
        pass
    
    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """
        Perform search and return standardized results.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of dicts with keys: title, url, snippet
        """
        pass
    
    @property
    @abstractmethod
    def max_results_limit(self) -> int:
        """Maximum results this provider can return per query."""
        pass


class DuckDuckGoProvider(BaseSearchProvider):
    """DuckDuckGo search implementation."""

    def __init__(self):
        self.base_url = "https://duckduckgo.com/html/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    @property
    def name(self) -> str:
        return "duckduckgo"

    @property
    def max_results_limit(self) -> int:
        return 50

    def _extract_real_url(self, duckduckgo_url: str) -> str:
        """
        Extract the real URL from DuckDuckGo's redirect URL.

        DuckDuckGo returns URLs like:
        //duckduckgo.com/l/?uddg=https%3A%2F%2Fen.wikipedia.org%2Fwiki%2FParis

        We need to extract and decode the 'uddg' parameter to get the actual URL.
        """
        if not duckduckgo_url:
            return duckduckgo_url

        # Handle protocol-relative URLs (//duckduckgo.com/...)
        if duckduckgo_url.startswith('//'):
            duckduckgo_url = 'https:' + duckduckgo_url

        try:
            parsed = urlparse(duckduckgo_url)
            query_params = parse_qs(parsed.query)

            if 'uddg' in query_params:
                real_url = query_params['uddg'][0]
                return unquote(real_url)

            return duckduckgo_url

        except Exception as e:
            logger.warning(f"Failed to extract real URL from {duckduckgo_url}: {e}")
            return duckduckgo_url

    def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """
        Perform a web search using DuckDuckGo.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of search results with title, url, and snippet
        """
        try:
            params = {"q": query, "kl": "us-en"}

            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            results = []

            for result in soup.find_all('div', class_='result')[:max_results]:
                title_tag = result.find('a', class_='result__a')
                snippet_tag = result.find('a', class_='result__snippet')

                if title_tag and snippet_tag:
                    title = title_tag.get_text(strip=True)
                    raw_url = title_tag.get('href', '')
                    url = self._extract_real_url(raw_url)
                    snippet = snippet_tag.get_text(strip=True)

                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet
                    })

            return results

        except requests.RequestException as e:
            logger.error(f"DuckDuckGo search request failed: {e}")
            raise WebSearchError(f"DuckDuckGo search request failed: {e}")
        except Exception as e:
            logger.error(f"DuckDuckGo search parsing failed: {e}")
            raise WebSearchError(f"DuckDuckGo search parsing failed: {e}")


class GooglePSEProvider(BaseSearchProvider):
    """Google Programmable Search Engine (Custom Search API) implementation."""

    def __init__(self, api_key: str, engine_id: str):
        self.api_key = api_key
        self.engine_id = engine_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    @property
    def name(self) -> str:
        return "google"

    @property
    def max_results_limit(self) -> int:
        return 10  # Google PSE API limitation

    def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """
        Perform a web search using Google PSE.

        Args:
            query: Search query string
            max_results: Maximum number of results to return (1-10, Google PSE limit)

        Returns:
            List of search results with title, url, and snippet

        Raises:
            WebSearchError: If API credentials are invalid or quota exceeded
        """
        try:
            # Google PSE API has a hard limit of 10 results
            if max_results > 10:
                logger.warning(f"Google PSE max results capped from {max_results} to 10 (API limitation)")
                max_results = 10

            params = {
                "key": self.api_key,
                "cx": self.engine_id,
                "q": query,
                "num": max(1, min(10, max_results))  # Ensure 1-10 range
            }

            response = requests.get(
                self.base_url,
                params=params,
                timeout=10
            )

            if response.status_code == 401:
                logger.error("Google PSE authentication failed")
                raise WebSearchError("Google PSE authentication failed. Check GOOGLE_PSE_API_KEY.")
            elif response.status_code == 403:
                logger.error("Google PSE quota exceeded")
                raise WebSearchError("Google PSE quota exceeded. 100 queries/day limit on free tier.")
            elif response.status_code == 400:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                if "cx" in error_msg.lower() or "engine" in error_msg.lower():
                    logger.error(f"Invalid Google PSE Engine ID: {error_msg}")
                    raise WebSearchError("Invalid Google PSE Engine ID. Check GOOGLE_PSE_ENGINE_ID.")
                logger.error(f"Google PSE bad request: {error_msg}")
                raise WebSearchError(f"Google PSE bad request: {error_msg}")

            response.raise_for_status()

            data = response.json()
            items = data.get("items", [])

            results = []
            for item in items:
                result = {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", "")
                }
                results.append(result)

            return results

        except WebSearchError:
            raise
        except requests.RequestException as e:
            logger.error(f"Google PSE search request failed: {e}")
            raise WebSearchError(f"Google PSE search request failed: {e}")
        except Exception as e:
            logger.error(f"Google PSE search parsing failed: {e}")
            raise WebSearchError(f"Google PSE search parsing failed: {e}")


def get_providers() -> dict[str, BaseSearchProvider]:
    """
    Initialize and return all available search providers.
    
    Returns:
        Dictionary mapping provider names to provider instances
    """
    providers: dict[str, BaseSearchProvider] = {}
    
    # Always add DuckDuckGo provider (no credentials required)
    providers["duckduckgo"] = DuckDuckGoProvider()
    
    # Add Google PSE provider if credentials are available
    google_api_key = os.getenv("GOOGLE_PSE_API_KEY")
    google_engine_id = os.getenv("GOOGLE_PSE_ENGINE_ID")
    
    if google_api_key and google_engine_id:
        providers["google"] = GooglePSEProvider(google_api_key, google_engine_id)
        logger.info("Google PSE provider initialized")
    else:
        logger.info("Google PSE provider not initialized (missing credentials)")
    
    return providers


# Initialize providers
providers = get_providers()

mcp = FastMCP(
    "web-search-server",
    instructions="Provides web search capabilities using DuckDuckGo and Google PSE. "
                 "Use the web_search tool to find information on the web.",
)


def validate_provider(provider: str) -> str:
    """
    Validate provider name and return normalized version.
    
    Args:
        provider: Provider name to validate
        
    Returns:
        Normalized provider name
        
    Raises:
        ValueError: If provider is invalid
    """
    provider = provider.lower().strip()
    
    if provider == "auto":
        default_provider = os.getenv("DEFAULT_SEARCH_PROVIDER", "duckduckgo")
        return default_provider
    
    if provider not in providers:
        available = list(providers.keys())
        raise ValueError(f"Unknown provider '{provider}'. Available: {available}")
    
    return provider


def perform_search(query: str, provider_name: str, max_results: int) -> dict:
    """
    Perform search with the specified provider.
    
    Args:
        query: Search query string
        provider_name: Name of the provider to use
        max_results: Maximum number of results
        
    Returns:
        Dictionary containing search results and metadata
        
    Raises:
        WebSearchError: If search fails
    """
    provider = providers[provider_name]
    
    # Validate max_results against provider limit
    if max_results > provider.max_results_limit:
        logger.warning(
            f"max_results ({max_results}) exceeds {provider.name} limit ({provider.max_results_limit}). "
            f"Capping to {provider.max_results_limit}."
        )
        max_results = provider.max_results_limit
    
    results = provider.search(query, max_results)
    
    return {
        "query": query,
        "provider": provider.name,
        "results": results,
        "count": len(results)
    }


def try_fallback_search(query: str, failed_provider: str, max_results: int) -> dict:
    """
    Attempt fallback search with alternative provider.
    
    Args:
        query: Search query string
        failed_provider: Name of the provider that failed
        max_results: Maximum number of results
        
    Returns:
        Dictionary containing search results and metadata
        
    Raises:
        WebSearchError: If fallback search also fails
    """
    fallback_map = {
        "duckduckgo": "google",
        "google": "duckduckgo"
    }
    
    fallback_provider = fallback_map.get(failed_provider)
    
    if fallback_provider and fallback_provider in providers:
        logger.info(f"Attempting fallback to {fallback_provider}")
        try:
            return perform_search(query, fallback_provider, max_results)
        except WebSearchError as e:
            logger.error(f"Fallback provider {fallback_provider} also failed: {e}")
            raise
    
    raise WebSearchError(f"No fallback provider available for {failed_provider}")


@mcp.tool
def web_search(
    query: str,
    max_results: int = 10,
    provider: str = "auto"
) -> str:
    """
    Perform a web search using the specified provider.
    
    Args:
        query: The search query string
        max_results: Maximum number of results to return (1-50, default: 10)
        provider: Search provider to use:
                  - "auto": Use default provider (env-configurable, default: duckduckgo)
                  - "duckduckgo": Use DuckDuckGo (50 results max, no auth required)
                  - "google": Use Google PSE (10 results max, requires API credentials)
    
    Returns:
        JSON string containing search results with title, url, and snippet
    """
    try:
        if not query or not query.strip():
            return json.dumps({
                "error": "Search query cannot be empty",
                "query": query,
                "provider": None,
                "results": [],
                "count": 0
            }, indent=2)
        
        # Validate and normalize provider
        try:
            provider_name = validate_provider(provider)
        except ValueError as e:
            return json.dumps({
                "error": str(e),
                "query": query,
                "provider": None,
                "results": [],
                "count": 0
            }, indent=2)
        
        max_results = max(1, min(50, max_results))
        
        # Attempt search with primary provider
        try:
            response_data = perform_search(query.strip(), provider_name, max_results)
            logger.info(f"Search completed for '{query}' using {provider_name}: {response_data['count']} results found")
            return json.dumps(response_data, indent=2)
        
        except WebSearchError as e:
            # Check if fallback is enabled
            enable_fallback = os.getenv("ENABLE_FALLBACK", "false").lower() == "true"
            
            if enable_fallback:
                try:
                    response_data = try_fallback_search(query.strip(), provider_name, max_results)
                    response_data["warning"] = f"Primary provider '{provider_name}' failed, used fallback"
                    logger.info(f"Fallback search completed for '{query}' using {response_data['provider']}")
                    return json.dumps(response_data, indent=2)
                except WebSearchError:
                    pass  # Fall through to error response
            
            return json.dumps({
                "error": str(e),
                "query": query,
                "provider": provider_name,
                "results": [],
                "count": 0
            }, indent=2)

    except Exception as e:
        logger.exception("Unexpected error in web_search")
        return json.dumps({
            "error": f"Unexpected error: {e}",
            "query": query,
            "provider": None,
            "results": [],
            "count": 0
        }, indent=2)


# Custom health check route (available alongside MCP endpoint)
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint."""
    try:
        provider_status = {}
        
        for name, provider in providers.items():
            try:
                test_results = provider.search("test", 1)
                provider_status[name] = {
                    "status": "healthy",
                    "max_results": provider.max_results_limit
                }
            except Exception as e:
                provider_status[name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        return JSONResponse({
            "status": "healthy",
            "message": "Web search service is operational",
            "providers": provider_status
        })
    except Exception as e:
        return JSONResponse({
            "status": "unhealthy",
            "message": f"Health check failed: {e}",
            "providers": {}
        }, status_code=503)


if __name__ == "__main__":
    logger.info("Starting MCP Web Search Server...")
    available_providers = list(providers.keys())
    logger.info(f"Available providers: {available_providers}")
    mcp.run(transport="http", host="0.0.0.0", port=8000)
