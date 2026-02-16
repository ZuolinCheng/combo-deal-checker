# tests/test_amazon.py
import pytest
from scrapers.amazon import parse_amazon_result, lookup_individual_price_from_text, AmazonScraper
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
