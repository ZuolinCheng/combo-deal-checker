# tests/test_newegg.py
import pytest
from scrapers.newegg import parse_combo_item, NeweggScraper
from config import Config


def test_parse_combo_item_full():
    raw = {
        "title": "AMD Ryzen 7 9800X3D + ASUS ROG STRIX X870E-E + G.SKILL 32GB DDR5-6000",
        "price": "$899.99",
        "url": "https://www.newegg.com/combo/12345",
        "components": [
            {"name": "AMD Ryzen 7 9800X3D", "category": "cpu"},
            {"name": "ASUS ROG STRIX X870E-E", "category": "motherboard"},
            {"name": "G.SKILL Trident Z5 32GB DDR5-6000", "category": "ram"},
        ],
    }
    deal = parse_combo_item(raw)
    assert deal.retailer == "Newegg"
    assert deal.combo_price == 899.99
    assert deal.combo_type == "CPU+MB+RAM"
    assert len(deal.components) == 3


def test_parse_combo_item_cpu_ram_only():
    raw = {
        "title": "AMD Ryzen 5 9600X + G.SKILL 32GB DDR5-6000",
        "price": "$399.99",
        "url": "https://www.newegg.com/combo/67890",
        "components": [
            {"name": "AMD Ryzen 5 9600X", "category": "cpu"},
            {"name": "G.SKILL 32GB DDR5-6000", "category": "ram"},
        ],
    }
    deal = parse_combo_item(raw)
    assert deal.combo_type == "CPU+RAM"
    assert len(deal.components) == 2


def test_newegg_scraper_init():
    scraper = NeweggScraper(Config())
    assert scraper.retailer_name == "NeweggScraper"
