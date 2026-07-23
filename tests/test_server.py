#!/usr/bin/env python3
"""
Unit tests for MCP Web Search Server

Run with: python -m pytest tests/ -v
"""

import json
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, 'src')


class TestDuckDuckGoProvider(unittest.TestCase):
    """Test DuckDuckGo provider functionality."""

    def setUp(self):
        """Set up test fixtures."""
        from server import DuckDuckGoProvider
        self.provider = DuckDuckGoProvider()

    def test_provider_name(self):
        """Test provider name is correct."""
        self.assertEqual(self.provider.name, "duckduckgo")

    def test_max_results_limit(self):
        """Test max results limit is 50."""
        self.assertEqual(self.provider.max_results_limit, 50)

    def test_extract_real_url_with_uddg(self):
        """Test extracting real URL from DuckDuckGo redirect with uddg parameter."""
        test_cases = [
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
                result = self.provider._extract_real_url(input_url)
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
                result = self.provider._extract_real_url(url)
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
                result = self.provider._extract_real_url(url)
                self.assertIsNotNone(result)


class TestGooglePSEProvider(unittest.TestCase):
    """Test Google PSE provider functionality."""

    def setUp(self):
        """Set up test fixtures."""
        from server import GooglePSEProvider
        self.api_key = "test_api_key"
        self.engine_id = "test_engine_id"
        self.provider = GooglePSEProvider(self.api_key, self.engine_id)

    def test_provider_name(self):
        """Test provider name is correct."""
        self.assertEqual(self.provider.name, "google")

    def test_max_results_limit(self):
        """Test max results limit is 10."""
        self.assertEqual(self.provider.max_results_limit, 10)

    def test_initialization(self):
        """Test provider stores credentials."""
        self.assertEqual(self.provider.api_key, self.api_key)
        self.assertEqual(self.provider.engine_id, self.engine_id)

    @patch('requests.get')
    def test_search_success(self, mock_get):
        """Test successful search."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "title": "Test Result",
                    "link": "https://example.com",
                    "snippet": "Test snippet"
                }
            ]
        }
        mock_get.return_value = mock_response

        results = self.provider.search("test query", 5)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Test Result")
        self.assertEqual(results[0]["url"], "https://example.com")
        self.assertEqual(results[0]["snippet"], "Test snippet")

    @patch('requests.get')
    def test_search_empty_results(self, mock_get):
        """Test search with no results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        results = self.provider.search("test query", 5)

        self.assertEqual(len(results), 0)

    @patch('requests.get')
    def test_search_auth_error(self, mock_get):
        """Test authentication error handling."""
        from server import WebSearchError

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        with self.assertRaises(WebSearchError) as context:
            self.provider.search("test query", 5)

        self.assertIn("authentication failed", str(context.exception).lower())

    @patch('requests.get')
    def test_search_quota_exceeded(self, mock_get):
        """Test quota exceeded error handling."""
        from server import WebSearchError

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        with self.assertRaises(WebSearchError) as context:
            self.provider.search("test query", 5)

        self.assertIn("quota exceeded", str(context.exception).lower())


class TestProviderUtilities(unittest.TestCase):
    """Test provider utility functions."""

    def setUp(self):
        """Set up test fixtures."""
        from server import get_providers, validate_provider
        self.get_providers = get_providers
        self.validate_provider = validate_provider

    @patch.dict('os.environ', {}, clear=True)
    def test_get_providers_no_google_creds(self):
        """Test providers without Google credentials."""
        from server import get_providers
        providers = get_providers()

        self.assertIn("duckduckgo", providers)
        self.assertNotIn("google", providers)

    @patch.dict('os.environ', {
        'GOOGLE_PSE_API_KEY': 'test_key',
        'GOOGLE_PSE_ENGINE_ID': 'test_engine'
    })
    def test_get_providers_with_google_creds(self):
        """Test providers with Google credentials."""
        from server import get_providers, GooglePSEProvider

        providers = get_providers()

        self.assertIn("duckduckgo", providers)
        self.assertIn("google", providers)
        self.assertIsInstance(providers["google"], GooglePSEProvider)

    def test_validate_provider_duckduckgo(self):
        """Test validating duckduckgo provider."""
        from server import providers

        with patch.dict('server.providers', {'duckduckgo': MagicMock()}, clear=False):
            result = self.validate_provider("duckduckgo")
            self.assertEqual(result, "duckduckgo")

    def test_validate_provider_auto_default(self):
        """Test auto provider uses default."""
        with patch.dict('os.environ', {'DEFAULT_SEARCH_PROVIDER': 'duckduckgo'}, clear=True):
            from server import validate_provider
            result = validate_provider("auto")
            self.assertEqual(result, "duckduckgo")

    def test_validate_provider_unknown(self):
        """Test unknown provider raises error."""
        from server import providers

        with patch.dict('server.providers', {'duckduckgo': MagicMock()}, clear=False):
            with self.assertRaises(ValueError) as context:
                self.validate_provider("unknown")

            self.assertIn("unknown", str(context.exception).lower())


class TestWebSearchTool(unittest.TestCase):
    """Test web_search tool function."""

    def setUp(self):
        """Set up test fixtures."""
        from server import providers

        # Mock providers for all tests
        mock_ddg = MagicMock()
        mock_ddg.search.return_value = [
            {"title": "DDG Result", "url": "https://ddg.com", "snippet": "DDG snippet"}
        ]
        mock_ddg.name = "duckduckgo"
        mock_ddg.max_results_limit = 50

        mock_google = MagicMock()
        mock_google.search.return_value = [
            {"title": "Google Result", "url": "https://google.com", "snippet": "Google snippet"}
        ]
        mock_google.name = "google"
        mock_google.max_results_limit = 10

        self.mock_providers = {
            "duckduckgo": mock_ddg,
            "google": mock_google
        }

    @patch('server.providers')
    def test_web_search_success_duckduckgo(self, mock_providers):
        """Test successful web search with DuckDuckGo."""
        from server import web_search

        mock_providers.__getitem__ = lambda self, key: self.mock_providers.get(key)
        mock_providers.get = lambda key: self.mock_providers.get(key)
        mock_providers.keys = lambda: self.mock_providers.keys()
        mock_providers.__contains__ = lambda self, key: key in self.mock_providers
        mock_providers.__iter__ = lambda self: iter(self.mock_providers.items())

        with patch.dict('server.providers', self.mock_providers, clear=True):
            result = json.loads(web_search("test query", provider="duckduckgo"))

        self.assertEqual(result["query"], "test query")
        self.assertEqual(result["provider"], "duckduckgo")
        self.assertEqual(result["count"], 1)

    def test_web_search_empty_query(self):
        """Test web search with empty query."""
        from server import web_search

        result = json.loads(web_search(""))

        self.assertIn("error", result)
        self.assertEqual(result["error"], "Search query cannot be empty")

    def test_web_search_whitespace_query(self):
        """Test web search with whitespace-only query."""
        from server import web_search

        result = json.loads(web_search("   "))

        self.assertIn("error", result)
        self.assertEqual(result["error"], "Search query cannot be empty")


class TestFastMCPServer(unittest.TestCase):
    """Test that the FastMCP server is configured correctly."""

    def test_server_has_tools(self):
        """Test that the MCP server has the web_search tool registered."""
        from server import mcp

        self.assertEqual(mcp.name, "web-search-server")

    def test_server_has_instructions(self):
        """Test that the MCP server has instructions set."""
        from server import mcp

        self.assertIsNotNone(mcp.instructions)
        self.assertIn("web search", mcp.instructions.lower())


class TestSearchFunctionality(unittest.TestCase):
    """Test core search functionality."""

    @patch('server.perform_search')
    def test_perform_search(self, mock_perform):
        """Test perform_search utility."""
        from server import perform_search

        mock_perform.return_value = {
            "query": "test",
            "provider": "duckduckgo",
            "results": [{"title": "Test", "url": "https://test.com", "snippet": "Snippet"}],
            "count": 1
        }

        with patch.dict('server.providers', {'duckduckgo': MagicMock()}, clear=False):
            result = perform_search("test", "duckduckgo", 5)

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["provider"], "duckduckgo")


if __name__ == '__main__':
    unittest.main(verbosity=2)
