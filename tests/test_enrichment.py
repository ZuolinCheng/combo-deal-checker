# tests/test_enrichment.py
from enrichment import enrich_deals
from models import ComboDeal, Component
from benchmarks import BenchmarkLookup


def test_enrich_deal_with_benchmark():
    deal = ComboDeal(retailer="Test", combo_type="CPU+MB+RAM", components=[
        Component("AMD Ryzen 9 9900X", "cpu", {}),
        Component("ASUS X870E", "motherboard", {}),
        Component("32GB DDR5-6000", "ram", {"ddr": 5, "capacity_gb": 32, "speed_mhz": 6000}),
    ], combo_price=900)
    enriched = enrich_deals([deal], BenchmarkLookup())
    assert enriched[0].cpu_name == "AMD Ryzen 9 9900X"
    assert enriched[0].cpu_sc_score > 0
    assert enriched[0].cpu_mc_score > 0
    assert enriched[0].cpu_cores == "12C/24T"
    assert enriched[0].ram_speed_mhz == 6000
    assert enriched[0].ram_capacity_gb == 32


def test_enrich_deal_unknown_cpu():
    deal = ComboDeal(retailer="Test", combo_type="CPU+RAM", components=[
        Component("Unknown CPU 9999X", "cpu", {}),
        Component("64GB DDR5-6400", "ram", {"ddr": 5, "capacity_gb": 64, "speed_mhz": 6400}),
    ], combo_price=600)
    enriched = enrich_deals([deal], BenchmarkLookup())
    assert enriched[0].cpu_name == "Unknown CPU 9999X"
    assert enriched[0].cpu_sc_score == 0
