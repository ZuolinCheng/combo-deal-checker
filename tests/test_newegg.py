# tests/test_newegg.py
import pytest
from scrapers.newegg import NEWEGG_SEARCH_URLS, parse_combo_item, NeweggScraper
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


def test_newegg_search_urls_include_mb_ram():
    lowered = [url.lower() for url in NEWEGG_SEARCH_URLS]
    assert any(
        ("motherboard+ram" in url or "motherboard+memory" in url)
        and all(token not in url for token in ("cpu+", "+cpu", "processor", "ryzen", "intel", "core+"))
        for url in lowered
    )


def test_newegg_search_urls_exclude_ddr5_keyword():
    assert all("ddr5" not in url.lower() for url in NEWEGG_SEARCH_URLS)


def test_newegg_search_urls_include_cpu_ram():
    lowered = [url.lower() for url in NEWEGG_SEARCH_URLS]
    assert any(
        ("cpu+ram" in url or "cpu+memory" in url)
        and "motherboard" not in url
        for url in lowered
    )


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


def test_detect_category_motherboard_with_ryzen_support_text():
    """Motherboard titles often mention Ryzen support and must not be marked CPU."""
    from scrapers.newegg import _detect_category
    name = (
        "GIGABYTE X870E AERO X3D WOOD AMD AM5 LGA 1718 Motherboard, ATX, "
        "Supports AMD Ryzen 9000/8000/7000 Series Processors"
    )
    assert _detect_category(name) == "motherboard"


def test_needs_detail_enrichment_for_cpu_sku_combo():
    """CPU SKU-only combos should trigger detail enrichment to recover CPU model text."""
    from scrapers.newegg import _needs_detail_enrichment

    raw = {
        "title": "CPU Motherboard Memory Combo - AMD 100-100001973WOF Bundle with MSI MAG X870 TOMAHAWK WIFI and V-color TMXSAL1664832KWK",
        "price": "$849.99",
        "url": "https://www.newegg.com/Product/ComboDealDetails?ItemList=Combo.4853708",
        "components": [
            {"name": "AMD 100-100001973WOF", "category": "cpu"},
            {"name": "MSI MAG X870 TOMAHAWK WIFI", "category": "motherboard"},
            {"name": "V-color TMXSAL1664832KWK", "category": "ram"},
        ],
    }

    deal = parse_combo_item(raw)
    assert _needs_detail_enrichment(deal) is True


def test_parse_ram_specs_vendor_sku_patterns():
    """Vendor SKU-only RAM names should still yield capacity/speed.

    Regression: combos like 4853094/4853708/4852644 were filtered as RAM 0GB.
    """
    from scrapers.newegg import _parse_ram_specs

    corsair = _parse_ram_specs("Corsair CMH32GX5M2N6400C36W")
    assert corsair.get("capacity_gb") == 32
    assert corsair.get("speed_mhz") == 6400

    vcolor = _parse_ram_specs("V-color TMXSAL1664832KWK")
    assert vcolor.get("capacity_gb") == 32
    assert vcolor.get("speed_mhz") == 6400

    patriot = _parse_ram_specs("Patriot Memory VEB516G6030W")
    assert patriot.get("capacity_gb") == 16
    assert patriot.get("speed_mhz") == 6000
