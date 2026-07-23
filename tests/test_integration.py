#!/usr/bin/env python3
"""
Integration tests for MCP Web Search Server

These tests verify end-to-end functionality against a running server.
The server uses FastMCP with Streamable HTTP transport.

Run with: python -m pytest tests/test_integration.py -v

Note: Requires the server to be running on localhost:8000.
To run server: python src/server.py
"""

import json
import subprocess
import unittest
import urllib.request
from urllib.error import HTTPError, URLError


def server_is_running() -> bool:
    """Check if the server is running."""
    try:
        req = urllib.request.Request(
            "http://localhost:8000/health",
            method='GET'
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


@unittest.skipUnless(server_is_running(), "Server not running on localhost:8000")
class TestMCPStreamableHTTP(unittest.TestCase):
    """Test MCP Streamable HTTP transport compliance."""

    def setUp(self):
        self.mcp_url = "http://localhost:8000/mcp"

    def _post_json_rpc(self, method, params=None, request_id=1):
        """Send a JSON-RPC request via POST to the MCP endpoint."""
        data = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }
        if params:
            data["params"] = params

        req = urllib.request.Request(
            self.mcp_url,
            data=json.dumps(data).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream',
            },
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))

    def test_initialize(self):
        """Test MCP initialize handshake."""
        result = self._post_json_rpc("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        })

        self.assertEqual(result["jsonrpc"], "2.0")
        self.assertIn("result", result)
        self.assertIn("capabilities", result["result"])
        self.assertIn("serverInfo", result["result"])

    def test_tools_list(self):
        """Test tools/list returns web_search tool."""
        result = self._post_json_rpc("tools/list")

        self.assertEqual(result["jsonrpc"], "2.0")
        self.assertIn("result", result)
        self.assertIn("tools", result["result"])

        tool_names = [t["name"] for t in result["result"]["tools"]]
        self.assertIn("web_search", tool_names)

    def test_tools_call_web_search(self):
        """Test calling web_search tool via MCP."""
        result = self._post_json_rpc("tools/call", {
            "name": "web_search",
            "arguments": {
                "query": "python programming",
                "max_results": 3
            }
        })

        self.assertEqual(result["jsonrpc"], "2.0")
        self.assertIn("result", result)
        self.assertIn("content", result["result"])

        content = result["result"]["content"][0]["text"]
        search_result = json.loads(content)

        self.assertEqual(search_result["query"], "python programming")
        self.assertIn("results", search_result)
        self.assertIn("count", search_result)
        self.assertIn("provider", search_result)

    def test_tools_call_with_provider_parameter(self):
        """Test web_search tool with provider parameter."""
        result = self._post_json_rpc("tools/call", {
            "name": "web_search",
            "arguments": {
                "query": "python programming",
                "max_results": 3,
                "provider": "duckduckgo"
            }
        })

        self.assertEqual(result["jsonrpc"], "2.0")
        self.assertIn("result", result)

        content = result["result"]["content"][0]["text"]
        search_result = json.loads(content)

        self.assertEqual(search_result["query"], "python programming")
        self.assertEqual(search_result["provider"], "duckduckgo")


@unittest.skipUnless(server_is_running(), "Server not running on localhost:8000")
class TestHealthEndpoint(unittest.TestCase):
    """Test the custom health check endpoint."""

    def test_health_returns_status(self):
        """Test /health returns a status."""
        req = urllib.request.Request("http://localhost:8000/health", method='GET')

        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))

        self.assertIn("status", result)
        self.assertIn(result["status"], ["healthy", "unhealthy"])
        self.assertIn("providers", result)

    def test_health_includes_provider_status(self):
        """Test health check includes provider status."""
        req = urllib.request.Request("http://localhost:8000/health", method='GET')

        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))

        self.assertIn("providers", result)
        # Should have at least duckduckgo provider
        self.assertIn("duckduckgo", result["providers"])


@unittest.skipUnless(server_is_running(), "Server not running on localhost:8000")
class TestSearchResultFormat(unittest.TestCase):
    """Test search result quality."""

    def _search(self, query: str, max_results: int = 3, provider: str = None) -> dict:
        """Perform a search via MCP tools/call."""
        args = {
            "query": query,
            "max_results": max_results
        }
        if provider:
            args["provider"] = provider

        data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 1,
            "params": {
                "name": "web_search",
                "arguments": args
            }
        }

        req = urllib.request.Request(
            "http://localhost:8000/mcp",
            data=json.dumps(data).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream',
            },
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))

        return json.loads(result["result"]["content"][0]["text"])

    def test_urls_are_not_redirects(self):
        """Test that URLs are decoded and not DuckDuckGo redirects."""
        result = self._search("python")

        for item in result["results"]:
            self.assertNotIn("//duckduckgo.com/l/", item["url"])
            self.assertTrue(
                item["url"].startswith(('http://', 'https://')),
                f"URL {item['url']} does not start with http:// or https://"
            )

    def test_results_have_required_fields(self):
        """Test that results have all required fields."""
        result = self._search("python")

        for item in result["results"]:
            self.assertIn("title", item)
            self.assertIn("url", item)
            self.assertIn("snippet", item)
            self.assertTrue(len(item["title"]) > 0)
            self.assertTrue(len(item["url"]) > 0)
            self.assertTrue(len(item["snippet"]) > 0)

    def test_provider_is_reported(self):
        """Test that search results include provider information."""
        result = self._search("python", provider="duckduckgo")

        self.assertIn("provider", result)
        self.assertEqual(result["provider"], "duckduckgo")


@unittest.skipUnless(server_is_running(), "Server not running on localhost:8000")
class TestErrorHandling(unittest.TestCase):
    """Test error handling."""

    def test_empty_query_error(self):
        """Test error response for empty query."""
        data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 1,
            "params": {
                "name": "web_search",
                "arguments": {
                    "query": "",
                    "max_results": 3
                }
            }
        }

        req = urllib.request.Request(
            "http://localhost:8000/mcp",
            data=json.dumps(data).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream',
            },
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))

        content = json.loads(result["result"]["content"][0]["text"])
        self.assertIn("error", content)
        self.assertEqual(content["error"], "Search query cannot be empty")

    def test_unknown_provider_error(self):
        """Test error response for unknown provider."""
        data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 1,
            "params": {
                "name": "web_search",
                "arguments": {
                    "query": "test",
                    "provider": "unknown_provider"
                }
            }
        }

        req = urllib.request.Request(
            "http://localhost:8000/mcp",
            data=json.dumps(data).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream',
            },
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))

        content = json.loads(result["result"]["content"][0]["text"])
        self.assertIn("error", content)
        self.assertIn("unknown", content["error"].lower())


if __name__ == '__main__':
    unittest.main(verbosity=2)
