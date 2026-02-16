# tests/test_microcenter.py
import pytest
from scrapers.microcenter import parse_bundle_item, MicroCenterScraper
from config import Config


def test_parse_bundle_item():
    raw = {
        "title": "AMD Ryzen 7 9800X3D + ASUS TUF X870 + G.SKILL 32GB DDR5-6000",
        "price": "$799.97",
        "url": "https://www.microcenter.com/product/combo/123",
        "components": [
            {"name": "AMD Ryzen 7 9800X3D", "category": "cpu"},
            {"name": "ASUS TUF Gaming X870-PLUS", "category": "motherboard"},
            {"name": "G.SKILL 32GB DDR5-6000", "category": "ram"},
        ],
    }
    deal = parse_bundle_item(raw)
    assert deal.retailer == "MicroCenter"
    assert deal.combo_price == 799.97
    assert deal.combo_type == "CPU+MB+RAM"


def test_parse_bundle_item_cpu_ram():
    raw = {
        "title": "Intel Core i5-14600K + Kingston 32GB DDR5-5600",
        "price": "$349.99",
        "url": "https://www.microcenter.com/product/combo/456",
        "components": [
            {"name": "Intel Core i5-14600K", "category": "cpu"},
            {"name": "Kingston FURY 32GB DDR5-5600", "category": "ram"},
        ],
    }
    deal = parse_bundle_item(raw)
    assert deal.combo_type == "CPU+RAM"
    assert len(deal.components) == 2


def test_microcenter_scraper_init():
    scraper = MicroCenterScraper(Config())
    assert scraper.retailer_name == "MicroCenterScraper"


def test_microcenter_scraper_zip_code():
    config = Config(microcenter_zip="10001")
    scraper = MicroCenterScraper(config)
    assert scraper.config.microcenter_zip == "10001"
