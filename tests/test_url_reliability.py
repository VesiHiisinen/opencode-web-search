#!/usr/bin/env python3
"""
Test to validate that websearch MCP returns consistently fetchable URLs.

This test:
1. Uses MCP web search to find pages
2. Fetches content from returned URLs using webfetch
3. Verifies URLs are consistently accessible (not just 9/10 times)

These 10 stable test targets are chosen because they:
- Are reliable, long-lived pages
- Have stable URLs that don't change
- Return consistent HTTP 200 responses
- Have predictable content for verification

Run with: python -m pytest tests/test_url_reliability.py -v

Note: Requires the MCP server to be running.
"""

import json
import subprocess
import sys
import unittest
import urllib.request
from urllib.error import HTTPError, URLError
from typing import Dict, List, Any, Tuple
import time


# 10 Stable test targets with expected content signatures
# These are chosen for reliability and long-term availability
STABLE_TEST_TARGETS: List[Dict[str, Any]] = [
    {
        "name": "Wikipedia Main Page",
        "search_query": "Wikipedia main page",
        "expected_in_content": ["Wikipedia", "Free Encyclopedia"],
        "min_results": 1
    },
    {
        "name": "MDN Web Docs",
        "search_query": "MDN Web Docs Mozilla",
        "expected_in_content": ["MDN", "Web", "Documentation"],
        "min_results": 1
    },
    {
        "name": "Python Documentation",
        "search_query": "Python official documentation",
        "expected_in_content": ["Python", "documentation"],
        "min_results": 1
    },
    {
        "name": "GitHub",
        "search_query": "GitHub homepage",
        "expected_in_content": ["GitHub", "build", "ship"],
        "min_results": 1
    },
    {
        "name": "Stack Overflow",
        "search_query": "Stack Overflow programming",
        "expected_in_content": ["Stack", "Overflow"],
        "min_results": 1
    },
    {
        "name": "W3C Standards",
        "search_query": "W3C World Wide Web Consortium",
        "expected_in_content": ["W3C", "Web", "Standards"],
        "min_results": 1
    },
    {
        "name": "Git Documentation",
        "search_query": "Git official documentation",
        "expected_in_content": ["Git", "documentation", "version control"],
        "min_results": 1
    },
    {
        "name": "Docker Documentation",
        "search_query": "Docker official documentation",
        "expected_in_content": ["Docker", "containers", "documentation"],
        "min_results": 1
    },
    {
        "name": "NPM Registry",
        "search_query": "NPM node package manager",
        "expected_in_content": ["NPM", "packages", "JavaScript"],
        "min_results": 1
    },
    {
        "name": "JSON Specification",
        "search_query": "JSON specification ECMA",
        "expected_in_content": ["JSON", "JavaScript", "Object"],
        "min_results": 1
    }
]


class URLFetcher:
    """Simple URL fetcher to test if URLs from websearch are accessible."""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def fetch(self, url: str, max_retries: int = 3) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Fetch URL content with retries.
        
        Args:
            url: URL to fetch
            max_retries: Number of retry attempts
            
        Returns:
            Tuple of (success: bool, content: str, metadata: dict)
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers=headers, method='GET')
                
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    content = response.read().decode('utf-8', errors='ignore')
                    metadata = {
                        'status_code': response.getcode(),
                        'content_length': len(content),
                        'url': response.geturl(),  # Final URL after redirects
                        'attempts': attempt + 1
                    }
                    return True, content, metadata
                    
            except HTTPError as e:
                last_error = f"HTTP {e.code}: {e.reason}"
                if e.code in [500, 502, 503, 504]:  # Server errors, retry
                    time.sleep(0.5 * (attempt + 1))
                    continue
                break  # Don't retry client errors
                
            except URLError as e:
                last_error = f"URL Error: {e.reason}"
                time.sleep(0.5 * (attempt + 1))
                continue
                
            except Exception as e:
                last_error = f"Error: {str(e)}"
                time.sleep(0.5 * (attempt + 1))
                continue
        
        return False, "", {
            'error': last_error,
            'attempts': max_retries,
            'url': url
        }


class TestWebSearchURLReliability(unittest.TestCase):
    """Test that websearch MCP returns consistently fetchable URLs."""
    
    @classmethod
    def setUpClass(cls):
        """Check if MCP server is running."""
        cls.base_url = "http://localhost:8000"
        cls.mcp_endpoint = f"{cls.base_url}/mcp"
        cls.server_available = cls._is_server_running()
        cls.fetcher = URLFetcher()
    
    @staticmethod
    def _is_server_running() -> bool:
        """Check if the MCP server is running."""
        try:
            req = urllib.request.Request(
                "http://localhost:8000/health",
                method='GET',
                timeout=5
            )
            with urllib.request.urlopen(req) as response:
                return response.getcode() == 200
        except:
            return False
    
    def _send_json_rpc(self, method: str, params: Dict = None, request_id: int = 1) -> Dict:
        """Send JSON-RPC request to MCP server."""
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
            method='POST',
            timeout=10
        )
        
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    
    def _search_via_mcp(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Perform web search via MCP server.
        
        Returns:
            List of search results with title, url, snippet
        """
        result = self._send_json_rpc("tools/call", {
            "name": "web_search",
            "arguments": {
                "query": query,
                "max_results": max_results
            }
        })
        
        if "error" in result:
            raise Exception(f"MCP search error: {result['error']}")
        
        # Parse the search result from MCP response
        content = result["result"]["content"][0]["text"]
        search_data = json.loads(content)
        
        return search_data.get("results", [])
    
    @unittest.skipUnless(
        _is_server_running(),
        "MCP server not running at localhost:8000"
    )
    def test_server_is_healthy(self):
        """Verify MCP server is healthy before running tests."""
        req = urllib.request.Request(
            f"{self.base_url}/health",
            method='GET'
        )
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            self.assertEqual(data.get("status"), "healthy")
    
    @unittest.skipUnless(
        _is_server_running(),
        "MCP server not running at localhost:8000"
    )
    def test_all_stable_targets_return_fetchable_urls(self):
        """
        Main test: Search for all stable targets and verify URLs are fetchable.
        
        This test validates that:
        1. MCP websearch returns results for all targets
        2. URLs returned are not DuckDuckGo redirects
        3. URLs can be fetched successfully (HTTP 200)
        4. Content contains expected text
        """
        results_summary = []
        failures = []
        
        for target in STABLE_TEST_TARGETS:
            with self.subTest(target=target["name"]):
                try:
                    # Step 1: Search via MCP
                    search_results = self._search_via_mcp(
                        target["search_query"],
                        max_results=3
                    )
                    
                    self.assertGreaterEqual(
                        len(search_results),
                        target["min_results"],
                        f"Expected at least {target['min_results']} results for {target['name']}"
                    )
                    
                    # Step 2: Try to fetch each result URL
                    fetched_count = 0
                    for result in search_results:
                        url = result.get("url", "")
                        
                        # Skip DuckDuckGo redirect URLs
                        if "duckduckgo.com/l/" in url or "uddg=" in url:
                            failures.append({
                                "target": target["name"],
                                "issue": "URL is a redirect",
                                "url": url
                            })
                            continue
                        
                        # Step 3: Fetch the URL
                        success, content, metadata = self.fetcher.fetch(url)
                        
                        if not success:
                            failures.append({
                                "target": target["name"],
                                "issue": f"Failed to fetch: {metadata.get('error')}",
                                "url": url,
                                "attempts": metadata.get('attempts')
                            })
                            continue
                        
                        # Step 4: Verify content contains expected text
                        content_lower = content.lower()
                        found_expected = False
                        for expected_text in target["expected_in_content"]:
                            if expected_text.lower() in content_lower:
                                found_expected = True
                                break
                        
                        if not found_expected:
                            failures.append({
                                "target": target["name"],
                                "issue": f"Content missing expected text: {target['expected_in_content']}",
                                "url": url
                            })
                            continue
                        
                        fetched_count += 1
                        results_summary.append({
                            "target": target["name"],
                            "url": url,
                            "status_code": metadata.get("status_code"),
                            "content_length": metadata.get("content_length"),
                            "attempts": metadata.get("attempts")
                        })
                    
                    # Verify at least one URL was successfully fetched
                    self.assertGreater(
                        fetched_count,
                        0,
                        f"No fetchable URLs found for {target['name']}"
                    )
                    
                except Exception as e:
                    failures.append({
                        "target": target["name"],
                        "issue": f"Exception during test: {str(e)}",
                        "url": "N/A"
                    })
        
        # Print summary
        print("\n" + "="*80)
        print("URL RELIABILITY TEST SUMMARY")
        print("="*80)
        print(f"\nTotal targets tested: {len(STABLE_TEST_TARGETS)}")
        print(f"Successful fetches: {len(results_summary)}")
        print(f"Failures: {len(failures)}")
        
        if results_summary:
            print("\nSuccessful fetches:")
            for r in results_summary[:10]:  # Limit output
                print(f"  ✓ {r['target'][:40]:40} | Status: {r['status_code']} | "
                      f"Size: {r['content_length']:6} bytes | Attempts: {r['attempts']}")
        
        if failures:
            print("\nFailed targets:")
            for f in failures:
                print(f"  ✗ {f['target'][:40]:40} | Issue: {f['issue'][:50]}")
                print(f"    URL: {f['url'][:80]}")
        
        print("="*80 + "\n")
        
        # Final assertion: All targets should have at least one working URL
        failure_count = len(failures)
        self.assertEqual(
            failure_count,
            0,
            f"{failure_count} targets failed. See summary above for details."
        )
    
    @unittest.skipUnless(
        _is_server_running(),
        "MCP server not running at localhost:8000"
    )
    def test_urls_are_not_redirects(self):
        """Verify URLs returned are direct URLs, not DuckDuckGo redirects."""
        for target in STABLE_TEST_TARGETS[:3]:  # Sample 3 targets
            with self.subTest(target=target["name"]):
                search_results = self._search_via_mcp(target["search_query"], max_results=3)
                
                for result in search_results:
                    url = result.get("url", "")
                    # URLs should NOT be DuckDuckGo redirect URLs
                    self.assertNotIn(
                        "duckduckgo.com/l/",
                        url,
                        f"URL is a DuckDuckGo redirect: {url}"
                    )
                    self.assertNotIn(
                        "uddg=",
                        url,
                        f"URL contains redirect parameter: {url}"
                    )
    
    @unittest.skipUnless(
        _is_server_running(),
        "MCP server not running at localhost:8000"
    )
    def test_mcp_search_returns_required_fields(self):
        """Verify MCP search results contain all required fields."""
        search_results = self._search_via_mcp("Python programming", max_results=3)
        
        self.assertGreater(len(search_results), 0, "No search results returned")
        
        for result in search_results:
            # Check required fields
            self.assertIn("title", result, "Result missing 'title' field")
            self.assertIn("url", result, "Result missing 'url' field")
            self.assertIn("snippet", result, "Result missing 'snippet' field")
            
            # Check fields are not empty
            self.assertIsNotNone(result["title"])
            self.assertIsNotNone(result["url"])
            self.assertIsNotNone(result["snippet"])
            
            # Check URL format
            self.assertTrue(
                result["url"].startswith(("http://", "https://")),
                f"Invalid URL format: {result['url']}"
            )


class TestURLFetcher(unittest.TestCase):
    """Unit tests for the URLFetcher helper class."""
    
    def setUp(self):
        self.fetcher = URLFetcher(timeout=5)
    
    def test_fetch_valid_url(self):
        """Test fetching a known valid URL."""
        # Use a very stable URL
        success, content, metadata = self.fetcher.fetch(
            "https://www.wikipedia.org",
            max_retries=1
        )
        
        self.assertTrue(success, f"Failed to fetch: {metadata.get('error')}")
        self.assertEqual(metadata["status_code"], 200)
        self.assertGreater(metadata["content_length"], 0)
    
    def test_fetch_invalid_url(self):
        """Test handling of invalid URLs."""
        success, content, metadata = self.fetcher.fetch(
            "https://this-domain-does-not-exist-12345.com",
            max_retries=1
        )
        
        self.assertFalse(success)
        self.assertIn("error", metadata)
    
    def test_fetch_with_redirects(self):
        """Test that redirects are followed."""
        # http://wikipedia.org redirects to https://
        success, content, metadata = self.fetcher.fetch(
            "http://wikipedia.org",
            max_retries=1
        )
        
        if success:
            # Should end up at https://
            self.assertTrue(
                metadata["url"].startswith("https://"),
                f"Redirect not followed. Final URL: {metadata['url']}"
            )


if __name__ == '__main__':
    # Check if server is running
    if not TestWebSearchURLReliability._is_server_running():
        print("\n" + "!"*80)
        print("WARNING: MCP server not running at localhost:8000")
        print("Please start the server first:")
        print("  python src/server.py")
        print("!"*80 + "\n")
    
    unittest.main(verbosity=2)
