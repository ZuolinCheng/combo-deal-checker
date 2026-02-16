# tests/test_base_scraper.py
import pytest
from scrapers.base import BaseScraper
from config import Config


class DummyScraper(BaseScraper):
    """Concrete implementation for testing."""
    async def scrape(self):
        return []


def test_base_scraper_init():
    config = Config()
    scraper = DummyScraper(config)
    assert scraper.config == config
    assert scraper.retailer_name == "DummyScraper"


def test_random_delay_range():
    config = Config(min_delay=1.0, max_delay=2.0)
    scraper = DummyScraper(config)
    delay = scraper._get_random_delay()
    assert 1.0 <= delay <= 2.0
