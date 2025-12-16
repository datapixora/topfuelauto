import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.core.config import Settings
from app.providers.web_crawl import WebCrawlOnDemandProvider


class WebCrawlProviderTests(unittest.TestCase):
    def _provider(self):
        return WebCrawlOnDemandProvider(
            Settings(
                CRAWL_SEARCH_ALLOWLIST=["https://example.com/search?q={query}"],
                CRAWL_SEARCH_RATE_PER_MINUTE=5,
            )
        )

    @patch("app.providers.web_crawl.httpx.get")
    def test_non_html_response_is_ignored(self, mock_get):
        mock_get.return_value = SimpleNamespace(
            status_code=200,
            headers={"content-type": "application/json"},
            text="{}",
            url=SimpleNamespace(host="example.com"),
        )
        provider = self._provider()
        results = provider.crawl_sources("gtr")
        self.assertEqual(results, [])

    @patch("app.providers.web_crawl.httpx.get")
    def test_results_do_not_include_forbidden_fields(self, mock_get):
        html = '<html><body><a href="https://example.com/listing/1">2010 Nissan GT-R</a></body></html>'
        mock_get.return_value = SimpleNamespace(
            status_code=200,
            headers={"content-type": "text/html"},
            text=html,
            url=SimpleNamespace(host="example.com"),
        )
        provider = self._provider()
        results = provider.crawl_sources("gtr")
        self.assertEqual(len(results), 1)
        row = results[0]
        self.assertNotIn("vin", row)
        self.assertEqual(row["source_domain"], "example.com")
        self.assertEqual(row["title"], "2010 Nissan GT-R")
        self.assertIsNone(row.get("price"))
        self.assertIsNone(row.get("location"))


if __name__ == "__main__":
    unittest.main()

