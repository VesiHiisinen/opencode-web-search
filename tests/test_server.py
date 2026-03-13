#!/usr/bin/env python3
"""
Unit tests for MCP Web Search Server

Run with: python -m pytest tests/ -v
"""

import json
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import quote

# Add src to path
sys.path.insert(0, 'src')


class TestDuckDuckGoSearcher(unittest.TestCase):
    """Test DuckDuckGo search functionality."""
    
    @patch('server.requests')
    @patch('server.BeautifulSoup')
    def setUp(self, mock_bs4, mock_requests):
        """Set up test fixtures."""
        # Mock HAS_DEPENDENCIES to True
        import server as server_module
        server_module.HAS_DEPENDENCIES = True
        server_module.requests = mock_requests
        server_module.BeautifulSoup = mock_bs4
        
        self.searcher = server_module.DuckDuckGoSearcher()
    
    def test_extract_real_url_with_uddg(self):
        """Test extracting real URL from DuckDuckGo redirect with uddg parameter."""
        test_cases = [
            # (input, expected_output)
            (
                "//duckduckgo.com/l/?uddg=https%3A%2F%2Fen.wikipedia.org%2Fwiki%2FParis",
                "https://en.wikipedia.org/wiki/Paris"
            ),
            (
                "//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.britannica.com%2Fplace%2FParis",
                "https://www.britannica.com/place/Paris"
            ),
            (
                "//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.example.com%2Fpath%3Fquery%3Dvalue",
                "https://www.example.com/path?query=value"
            ),
        ]
        
        for input_url, expected in test_cases:
            with self.subTest(input_url=input_url):
                result = self.searcher._extract_real_url(input_url)
                self.assertEqual(result, expected)
    
    def test_extract_real_url_without_uddg(self):
        """Test extracting URL without uddg parameter (pass-through)."""
        test_urls = [
            "https://www.example.com",
            "http://test.org/path",
            "",
        ]
        
        for url in test_urls:
            with self.subTest(url=url):
                result = self.searcher._extract_real_url(url)
                self.assertEqual(result, url)
    
    def test_extract_real_url_malformed(self):
        """Test handling malformed URLs gracefully."""
        test_cases = [
            "not-a-url",
            "///",
            "?only=query",
        ]
        
        for url in test_cases:
            with self.subTest(url=url):
                # Should not raise exception
                result = self.searcher._extract_real_url(url)
                # Result should be either the original or a reasonable fallback
                self.assertIsNotNone(result)
    
    @patch('server.requests')
    @patch('server.BeautifulSoup')
    def test_search_success(self, mock_bs4, mock_requests):
        """Test successful search with mocked response."""
        # Create mock HTML response
        mock_response = MagicMock()
        mock_response.text = """
        <html>
        <body>
            <div class="result">
                <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com">Example Title</a>
                <a class="result__snippet">Example snippet text</a>
            </div>
        </body>
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response
        
        # Create mock BeautifulSoup
        mock_soup = MagicMock()
        mock_result = MagicMock()
        mock_title_tag = MagicMock()
        mock_title_tag.get_text.return_value = "Example Title"
        mock_title_tag.get.return_value = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com"
        mock_snippet_tag = MagicMock()
        mock_snippet_tag.get_text.return_value = "Example snippet text"
        
        mock_result.find.side_effect = [mock_title_tag, mock_snippet_tag]
        mock_soup.find_all.return_value = [mock_result]
        mock_bs4.return_value = mock_soup
        
        results = self.searcher.search("test query", max_results=1)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Example Title")
        self.assertEqual(results[0]["url"], "https://example.com")
        self.assertEqual(results[0]["snippet"], "Example snippet text")


class TestMCPServer(unittest.TestCase):
    """Test MCP server functionality."""
    
    def setUp(self):
        """Set up MCP server instance."""
        import server as server_module
        self.server = server_module.MCPServer()
    
    def test_initialization(self):
        """Test MCP server initialization."""
        self.assertEqual(self.server.server_info["name"], "web-search-server")
        self.assertEqual(self.server.server_info["version"], "1.0.0")
        self.assertIn("tools", self.server.capabilities)
    
    def test_tools_list(self):
        """Test tools/list request."""
        result = self.server._handle_tools_list(request_id=1)
        
        self.assertEqual(result["jsonrpc"], "2.0")
        self.assertEqual(result["id"], 1)
        self.assertIn("tools", result["result"])
        self.assertEqual(len(result["result"]["tools"]), 1)
        
        tool = result["result"]["tools"][0]
        self.assertEqual(tool["name"], "web_search")
        self.assertEqual(tool["description"], "Perform a web search using DuckDuckGo")
    
    def test_initialize(self):
        """Test initialize request."""
        params = {
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        }
        result = self.server._handle_initialize(request_id=1, params=params)
        
        self.assertEqual(result["jsonrpc"], "2.0")
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["result"]["protocolVersion"], "2024-11-05")
        self.assertIn("capabilities", result["result"])
        self.assertIn("serverInfo", result["result"])
    
    def test_ping(self):
        """Test ping request."""
        result = self.server._handle_ping(request_id=1)
        
        self.assertEqual(result["jsonrpc"], "2.0")
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["result"]["pong"], True)
    
    def test_handle_request_unknown_method(self):
        """Test handling unknown method."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "unknown_method",
            "id": 1
        }
        result = self.server.handle_request(request_data)
        
        self.assertEqual(result["jsonrpc"], "2.0")
        self.assertEqual(result["id"], 1)
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], -32601)


class TestWebSearchFunction(unittest.TestCase):
    """Test web_search function."""
    
    @patch('server.searcher')
    def test_web_search_success(self, mock_searcher):
        """Test successful web search."""
        import server as server_module
        
        mock_searcher.search.return_value = [
            {
                "title": "Test Result",
                "url": "https://example.com",
                "snippet": "Test snippet"
            }
        ]
        
        result = json.loads(server_module.web_search("test query"))
        
        self.assertEqual(result["query"], "test query")
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["title"], "Test Result")
    
    @patch('server.searcher', None)
    def test_web_search_no_searcher(self):
        """Test web search when searcher is not available."""
        import server as server_module
        
        result = json.loads(server_module.web_search("test query"))
        
        self.assertIn("error", result)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["query"], "test query")
    
    def test_web_search_empty_query(self):
        """Test web search with empty query."""
        import server as server_module
        
        result = json.loads(server_module.web_search(""))
        
        self.assertIn("error", result)
    
    def test_web_search_invalid_max_results(self):
        """Test web search with invalid max_results."""
        import server as server_module
        
        # Should not raise, should use default
        result = json.loads(server_module.web_search("test", max_results=100))
        self.assertEqual(result["query"], "test")


class TestSearchHealth(unittest.TestCase):
    """Test health check functionality."""
    
    @patch('server.searcher')
    def test_health_check_success(self, mock_searcher):
        """Test successful health check."""
        import server as server_module
        
        mock_searcher.search.return_value = []
        
        result = json.loads(server_module.search_health())
        
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(result["test_query_successful"], True)
    
    @patch('server.searcher', None)
    def test_health_check_no_searcher(self):
        """Test health check when searcher is not available."""
        import server as server_module
        
        result = json.loads(server_module.search_health())
        
        self.assertEqual(result["status"], "unhealthy")
        self.assertEqual(result["test_query_successful"], False)


if __name__ == '__main__':
    unittest.main(verbosity=2)
