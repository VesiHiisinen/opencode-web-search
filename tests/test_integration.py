#!/usr/bin/env python3
"""
Integration and E2E tests for MCP Web Search Server

These tests verify the MCP protocol compliance and end-to-end functionality.

Run with: python -m pytest tests/ -v

Note: Some tests require the server to be running.
To run server: python src/server.py
"""

import json
import subprocess
import sys
import time
import unittest
import urllib.request
from urllib.error import HTTPError


class TestMCPProtocolCompliance(unittest.TestCase):
    """Test MCP protocol compliance."""
    
    def setUp(self):
        """Set up base URL for tests."""
        self.base_url = "http://localhost:8000"
        self.mcp_endpoint = f"{self.base_url}/mcp"
    
    def _send_json_rpc(self, method, params=None, request_id=1):
        """Helper to send JSON-RPC requests."""
        data = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }
        if params:
            data["params"] = params
        
        req = urllib.request.Request(
            self.mcp_endpoint,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    
    @unittest.skipIf(
        subprocess.run(['curl', '-s', 'http://localhost:8000/health'], 
                      capture_output=True).returncode != 0,
        "Server not running"
    )
    def test_mcp_initialize(self):
        """Test MCP initialize request."""
        result = self._send_json_rpc("initialize", {
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        })
        
        self.assertEqual(result["jsonrpc"], "2.0")
        self.assertIn("result", result)
        self.assertEqual(result["result"]["protocolVersion"], "2024-11-05")
        self.assertIn("capabilities", result["result"])
        self.assertIn("serverInfo", result["result"])
    
    @unittest.skipIf(
        subprocess.run(['curl', '-s', 'http://localhost:8000/health'], 
                      capture_output=True).returncode != 0,
        "Server not running"
    )
    def test_mcp_tools_list(self):
        """Test MCP tools/list request."""
        result = self._send_json_rpc("tools/list")
        
        self.assertEqual(result["jsonrpc"], "2.0")
        self.assertIn("result", result)
        self.assertIn("tools", result["result"])
        self.assertGreater(len(result["result"]["tools"]), 0)
    
    @unittest.skipIf(
        subprocess.run(['curl', '-s', 'http://localhost:8000/health'], 
                      capture_output=True).returncode != 0,
        "Server not running"
    )
    def test_mcp_tools_call_web_search(self):
        """Test MCP tools/call request for web_search."""
        result = self._send_json_rpc("tools/call", {
            "name": "web_search",
            "arguments": {
                "query": "test",
                "max_results": 1
            }
        })
        
        self.assertEqual(result["jsonrpc"], "2.0")
        self.assertIn("result", result)
        self.assertIn("content", result["result"])
        
        # Parse the search result
        content = result["result"]["content"][0]["text"]
        search_result = json.loads(content)
        
        self.assertEqual(search_result["query"], "test")
        self.assertIn("results", search_result)
        self.assertIn("count", search_result)


class TestRESTEndpoints(unittest.TestCase):
    """Test REST API endpoints."""
    
    def setUp(self):
        """Set up base URL."""
        self.base_url = "http://localhost:8000"
    
    def _get(self, endpoint):
        """Helper to make GET requests."""
        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(url, method='GET')
        
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    
    @unittest.skipIf(
        subprocess.run(['curl', '-s', 'http://localhost:8000/health'], 
                      capture_output=True).returncode != 0,
        "Server not running"
    )
    def test_health_endpoint(self):
        """Test /health endpoint."""
        result = self._get("/health")
        
        self.assertIn("status", result)
        self.assertIn(result["status"], ["healthy", "unhealthy"])
    
    @unittest.skipIf(
        subprocess.run(['curl', '-s', 'http://localhost:8000/health'], 
                      capture_output=True).returncode != 0,
        "Server not running"
    )
    def test_search_endpoint(self):
        """Test /search endpoint."""
        result = self._get("/search?q=python&max_results=3")
        
        self.assertIn("query", result)
        self.assertEqual(result["query"], "python")
        self.assertIn("results", result)
        self.assertIn("count", result)


class TestSSEEConnection(unittest.TestCase):
    """Test Server-Sent Events endpoint."""
    
    @unittest.skipIf(
        subprocess.run(['curl', '-s', 'http://localhost:8000/health'], 
                      capture_output=True).returncode != 0,
        "Server not running"
    )
    def test_sse_endpoint_exists(self):
        """Test that SSE endpoint exists and returns valid events."""
        try:
            import urllib.request
            
            url = "http://localhost:8000/"
            req = urllib.request.Request(
                url,
                headers={'Accept': 'text/event-stream'}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                # Read first chunk
                data = response.read(1024).decode('utf-8')
                self.assertIn("event:", data)
        except Exception as e:
            self.fail(f"SSE endpoint failed: {e}")


class TestDockerIntegration(unittest.TestCase):
    """Test Docker integration (optional)."""
    
    @classmethod
    def setUpClass(cls):
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True
            )
            cls.docker_available = result.returncode == 0
        except Exception:
            cls.docker_available = False
    
    @unittest.skipUnless(
        subprocess.run(['docker', '--version'], capture_output=True).returncode == 0,
        "Docker not available"
    )
    def test_docker_build(self):
        """Test Docker image builds successfully."""
        result = subprocess.run(
            ['docker', 'build', '-t', 'web-search-test:latest', '.'],
            capture_output=True,
            text=True,
            cwd='/home/vettis/projects/ai/opencode/agentic-web-search'
        )
        
        self.assertEqual(
            result.returncode, 0,
            f"Docker build failed: {result.stderr}"
        )


class TestSearchResultFormat(unittest.TestCase):
    """Test search result format for model compatibility."""
    
    @unittest.skipIf(
        subprocess.run(['curl', '-s', 'http://localhost:8000/health'], 
                      capture_output=True).returncode != 0,
        "Server not running"
    )
    def test_urls_are_not_redirects(self):
        """Test that URLs are decoded and not DuckDuckGo redirects."""
        try:
            url = "http://localhost:8000/search?q=python&max_results=3"
            req = urllib.request.Request(url, method='GET')
            
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            for item in result["results"]:
                # URLs should not be DuckDuckGo redirect URLs
                self.assertNotIn("//duckduckgo.com/l/", item["url"])
                # URLs should be valid HTTP/HTTPS URLs
                self.assertTrue(
                    item["url"].startswith(('http://', 'https://')),
                    f"URL {item['url']} does not start with http:// or https://"
                )
        except Exception as e:
            self.fail(f"Test failed: {e}")
    
    @unittest.skipIf(
        subprocess.run(['curl', '-s', 'http://localhost:8000/health'], 
                      capture_output=True).returncode != 0,
        "Server not running"
    )
    def test_results_have_required_fields(self):
        """Test that results have all required fields."""
        try:
            url = "http://localhost:8000/search?q=python&max_results=3"
            req = urllib.request.Request(url, method='GET')
            
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            for item in result["results"]:
                self.assertIn("title", item)
                self.assertIn("url", item)
                self.assertIn("snippet", item)
                # Fields should not be empty
                self.assertIsNotNone(item["title"])
                self.assertIsNotNone(item["url"])
                self.assertIsNotNone(item["snippet"])
        except Exception as e:
            self.fail(f"Test failed: {e}")


class TestErrorHandling(unittest.TestCase):
    """Test error handling."""
    
    @unittest.skipIf(
        subprocess.run(['curl', '-s', 'http://localhost:8000/health'], 
                      capture_output=True).returncode != 0,
        "Server not running"
    )
    def test_empty_query_handling(self):
        """Test handling of empty search query."""
        try:
            url = "http://localhost:8000/search?q=&max_results=3"
            req = urllib.request.Request(url, method='GET')
            
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            # Should return empty results or error gracefully
            self.assertIn("results", result)
        except HTTPError as e:
            # 400 or other error is also acceptable
            self.assertIn(e.code, [200, 400, 422])


if __name__ == '__main__':
    unittest.main(verbosity=2)
