# tests/test_bhphoto.py
import pytest
from scrapers.bhphoto import BHPHOTO_SEARCH_QUERIES, parse_bh_item, BHPhotoScraper
from config import Config


def test_parse_bh_item():
    raw = {
        "title": "Intel Core i7-14700K + MSI Z790 + Kingston 32GB DDR5-6000 Kit",
        "price": "$749.00",
        "url": "https://www.bhphotovideo.com/c/product/bundle123",
        "components": [
            {"name": "Intel Core i7-14700K", "category": "cpu"},
            {"name": "MSI MAG Z790 TOMAHAWK", "category": "motherboard"},
            {"name": "Kingston FURY 32GB DDR5-6000", "category": "ram"},
        ],
    }
    deal = parse_bh_item(raw)
    assert deal.retailer == "BHPhoto"
    assert deal.combo_price == 749.0
    assert deal.combo_type == "CPU+MB+RAM"


def test_parse_bh_item_mb_ram():
    raw = {
        "title": "MSI MAG Z790 + Corsair 32GB DDR5-5600 Kit",
        "price": "$389.00",
        "url": "https://www.bhphotovideo.com/c/product/bundle456",
        "components": [
            {"name": "MSI MAG Z790 TOMAHAWK", "category": "motherboard"},
            {"name": "Corsair Vengeance 32GB DDR5-5600", "category": "ram"},
        ],
    }
    deal = parse_bh_item(raw)
    assert deal.combo_type == "MB+RAM"
    assert len(deal.components) == 2


def test_bhphoto_scraper_init():
    scraper = BHPhotoScraper(Config())
    assert scraper.retailer_name == "BHPhotoScraper"


def test_bhphoto_search_queries_include_mb_ram():
    lowered = [q.lower() for q in BHPHOTO_SEARCH_QUERIES]
    assert any(
        "motherboard" in q
        and ("ram" in q or "memory" in q)
        and all(token not in q for token in ("cpu", "processor", "ryzen", "intel", "core"))
        for q in lowered
    )


def test_bhphoto_search_queries_exclude_ddr5_keyword():
    assert all("ddr5" not in q.lower() for q in BHPHOTO_SEARCH_QUERIES)


def test_bhphoto_search_queries_include_cpu_ram():
    lowered = [q.lower() for q in BHPHOTO_SEARCH_QUERIES]
    assert any(
        ("cpu" in q or "processor" in q)
        and ("ram" in q or "memory" in q)
        and "motherboard" not in q
        for q in lowered
    )
