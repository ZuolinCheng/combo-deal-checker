# tests/test_amazon.py
import pytest
from scrapers.amazon import (
    AMAZON_SEARCH_QUERIES,
    parse_amazon_result,
    lookup_individual_price_from_text,
    AmazonScraper,
)
from config import Config


def test_parse_amazon_result():
    raw = {
        "title": "AMD Ryzen 7 9800X3D + MSI MAG X870 TOMAHAWK + Corsair 32GB DDR5-6000",
        "price": "$849.99",
        "url": "https://www.amazon.com/dp/B0COMBO123",
        "components": [
            {"name": "AMD Ryzen 7 9800X3D", "category": "cpu"},
            {"name": "MSI MAG X870 TOMAHAWK", "category": "motherboard"},
            {"name": "Corsair Vengeance 32GB DDR5-6000", "category": "ram"},
        ],
    }
    deal = parse_amazon_result(raw)
    assert deal.retailer == "Amazon"
    assert deal.combo_price == 849.99
    assert deal.combo_type == "CPU+MB+RAM"


def test_lookup_individual_price():
    price = lookup_individual_price_from_text("$449.99")
    assert price == 449.99


def test_lookup_individual_price_no_dollar_sign():
    price = lookup_individual_price_from_text("449.99")
    assert price == 449.99


def test_lookup_individual_price_with_commas():
    price = lookup_individual_price_from_text("$1,249.99")
    assert price == 1249.99


def test_lookup_individual_price_invalid():
    price = lookup_individual_price_from_text("not a price")
    assert price == 0.0


def test_amazon_scraper_init():
    scraper = AmazonScraper(Config())
    assert scraper.retailer_name == "AmazonScraper"


def test_amazon_search_queries_include_mb_ram():
    lowered = [q.lower() for q in AMAZON_SEARCH_QUERIES]
    assert any(
        "motherboard" in q
        and ("ram" in q or "memory" in q)
        and all(token not in q for token in ("cpu", "processor", "ryzen", "intel", "core"))
        for q in lowered
    )


def test_amazon_search_queries_exclude_ddr5_keyword():
    assert all("ddr5" not in q.lower() for q in AMAZON_SEARCH_QUERIES)


def test_amazon_search_queries_include_cpu_ram():
    lowered = [q.lower() for q in AMAZON_SEARCH_QUERIES]
    assert any(
        ("cpu" in q or "processor" in q)
        and ("ram" in q or "memory" in q)
        and "motherboard" not in q
        for q in lowered
    )
