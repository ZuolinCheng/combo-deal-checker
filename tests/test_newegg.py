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


# --- Bug #11: Relative URLs should be made absolute ---
def test_parse_combo_item_relative_url_becomes_absolute():
    """Newegg hrefs are relative — parse_combo_item should prepend base URL."""
    raw = {
        "title": "AMD Ryzen 7 9800X3D + ASUS X870E + G.SKILL 32GB DDR5-6000",
        "price": "$899.99",
        "url": "/Product/ComboDealDetails?ItemList=Combo.4853134",
        "components": [
            {"name": "AMD Ryzen 7 9800X3D", "category": "cpu"},
            {"name": "ASUS X870E", "category": "motherboard"},
            {"name": "G.SKILL 32GB DDR5-6000", "category": "ram"},
        ],
    }
    deal = parse_combo_item(raw)
    assert deal.url.startswith("https://www.newegg.com/")
    assert "Combo.4853134" in deal.url


def test_parse_combo_item_absolute_url_unchanged():
    """Already-absolute URLs should be left alone."""
    raw = {
        "title": "Test combo",
        "price": "$100",
        "url": "https://www.newegg.com/combo/12345",
        "components": [
            {"name": "Test CPU", "category": "cpu"},
            {"name": "Test RAM DDR5-6000 32GB", "category": "ram"},
        ],
    }
    deal = parse_combo_item(raw)
    assert deal.url == "https://www.newegg.com/combo/12345"


# --- Bug #12: RAM capacity regex should handle kit formats ---
def test_parse_ram_specs_kit_format_2x16():
    """'2x16GB DDR5-6000' should parse total capacity as 32GB."""
    from scrapers.newegg import _parse_ram_specs
    specs = _parse_ram_specs("G.Skill Trident Z5 2x16GB DDR5-6000")
    assert specs.get("capacity_gb") == 32


def test_parse_ram_specs_kit_format_2_x_16():
    """'2 x 16GB DDR5-6000' should parse total capacity as 32GB."""
    from scrapers.newegg import _parse_ram_specs
    specs = _parse_ram_specs("Corsair Vengeance 2 x 16GB DDR5-6400")
    assert specs.get("capacity_gb") == 32


def test_parse_ram_specs_total_already_stated():
    """'32GB (2x16GB) DDR5-6000' should still get 32GB (use first match)."""
    from scrapers.newegg import _parse_ram_specs
    specs = _parse_ram_specs("G.SKILL 32GB (2x16GB) DDR5-6000")
    assert specs.get("capacity_gb") == 32


# --- Bug #2: DDR5 should be inferred from search context ---
def test_parse_ram_specs_no_ddr_in_name():
    """Abbreviated RAM names like 'V-Color 32GB Memory' lack DDR version.
    When search context is DDR5, the scraper should still mark it as DDR5."""
    from scrapers.newegg import _parse_ram_specs
    # This tests the raw parser — it returns empty ddr when not in name
    specs = _parse_ram_specs("V-Color 32GB Memory")
    # The raw parser cannot infer DDR from context, but capacity should work
    assert specs.get("capacity_gb") == 32


def test_extract_prefix_categories_cpu_mb_memory():
    """Title prefix 'CPU Motherboard Memory Combo' → [cpu, motherboard, ram]."""
    from scrapers.newegg import _extract_prefix_categories
    cats = _extract_prefix_categories("CPU Motherboard Memory Combo - AMD 100-WOF Bundle with MSI MAG X870 + V-Color 32GB")
    assert cats == ["cpu", "motherboard", "ram"]


def test_extract_prefix_categories_reversed_order():
    """Title prefix 'Motherboard CPU Memory Combo' → [motherboard, cpu, ram]."""
    from scrapers.newegg import _extract_prefix_categories
    cats = _extract_prefix_categories("Motherboard CPU Memory Combo - GIGABYTE X870E Bundle with AMD Ryzen + RAM")
    assert cats == ["motherboard", "cpu", "ram"]


def test_extract_prefix_categories_no_prefix():
    """Titles without a combo prefix return empty list."""
    from scrapers.newegg import _extract_prefix_categories
    cats = _extract_prefix_categories("AMD Ryzen 7 9800X3D + ASUS ROG STRIX X870E-E")
    assert cats == []


def test_detect_category_ram_brand_skus():
    """Truncated RAM names with brand SKU prefixes should be detected as RAM."""
    from scrapers.newegg import _detect_category
    assert _detect_category("Corsair CMH32GX5M2B6400C36") == "ram"
    assert _detect_category("V-Color TMXS516G6400HC40ADC01") == "ram"
    assert _detect_category("Team Group FF3D516G6000HC38ADC01") == "ram"


def test_parse_combo_item_infers_ddr5_when_missing():
    """If RAM component lacks DDR version but search is DDR5, infer DDR5."""
    raw = {
        "title": "CPU Motherboard Memory Combo - AMD Ryzen 7 9850X3D CPU + ASUS X870E-Plus MB + V-Color DDR5 32GB Memory",
        "price": "$900",
        "url": "/Product/ComboDealDetails?ItemList=Combo.4853134",
        "components": [
            {"name": "AMD Ryzen 7 9850X3D CPU", "category": "cpu"},
            {"name": "ASUS X870E-Plus MB", "category": "motherboard"},
            {"name": "V-Color 32GB Memory", "category": "ram"},
        ],
    }
    deal = parse_combo_item(raw)
    ram = deal.get_component("ram")
    assert ram.specs.get("ddr") == 5
