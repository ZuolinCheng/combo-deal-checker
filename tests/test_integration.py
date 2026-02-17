# tests/test_integration.py
"""Integration test using mock data (no network)."""
from models import ComboDeal, Component
from benchmarks import BenchmarkLookup
from enrichment import enrich_deals
from filters import filter_deals
from output.terminal import render_deals_table
from output.html import render_html_report
from config import Config


def _make_deals():
    return [
        ComboDeal(
            retailer="Newegg",
            combo_type="CPU+MB+RAM",
            components=[
                Component("AMD Ryzen 9 9900X", "cpu", {}, 449.0),
                Component("ASUS ROG STRIX X870E-E", "motherboard", {}, 349.0),
                Component("G.SKILL 32GB DDR5-6000", "ram", {"ddr": 5, "capacity_gb": 32, "speed_mhz": 6000}, 129.0),
            ],
            combo_price=879.0,
            url="https://newegg.com/combo/1",
        ),
        ComboDeal(
            retailer="MicroCenter",
            combo_type="CPU+MB+RAM",
            components=[
                Component("AMD Ryzen 7 9800X3D", "cpu", {}, 449.0),
                Component("MSI MAG X870 TOMAHAWK", "motherboard", {}, 279.0),
                Component("Corsair 64GB DDR5-6400", "ram", {"ddr": 5, "capacity_gb": 64, "speed_mhz": 6400}, 199.0),
            ],
            combo_price=849.0,
            url="https://microcenter.com/combo/2",
        ),
        ComboDeal(
            retailer="Amazon",
            combo_type="CPU+RAM",
            components=[
                Component("Intel Core i7-14700K", "cpu", {}, 379.0),
                Component("Kingston 32GB DDR5-6000", "ram", {"ddr": 5, "capacity_gb": 32, "speed_mhz": 6000}, 119.0),
            ],
            combo_price=459.0,
            url="https://amazon.com/dp/3",
        ),
        ComboDeal(
            retailer="BHPhoto",
            combo_type="MB+RAM",
            components=[
                Component("ASUS TUF Gaming B650", "motherboard", {}, 179.0),
                Component("16GB DDR5-5600", "ram", {"ddr": 5, "capacity_gb": 16, "speed_mhz": 5600}, 59.0),
            ],
            combo_price=219.0,
            url="https://bhphoto.com/4",
        ),
    ]


def test_full_pipeline(tmp_path):
    config = Config()
    deals = _make_deals()

    # Calculate savings
    for d in deals:
        d.calculate_savings()

    # Enrich
    benchmark = BenchmarkLookup()
    deals = enrich_deals(deals, benchmark)

    # Filter
    filtered = filter_deals(deals, config)

    # Amazon CPU+RAM deal ($459) now passes budget (>= $100)
    # BHPhoto MB+RAM deal has 16GB RAM — filtered out
    # Should keep Newegg, MicroCenter, and Amazon deals
    assert len(filtered) == 3
    assert all(d.combo_price >= 100 for d in filtered)
    assert all(d.get_component("ram").specs.get("capacity_gb", 0) >= 32 for d in filtered)

    # Check enrichment worked
    for d in filtered:
        assert d.cpu_name != ""
        assert d.cpu_sc_score > 0

    # Terminal output
    output = render_deals_table(filtered)
    assert "Newegg" in output
    assert "MicroCenter" in output
    assert "Amazon" in output

    # HTML output
    html_path = render_html_report(filtered, output_dir=str(tmp_path))
    assert html_path.endswith(".html")
    with open(html_path) as f:
        html = f.read()
    assert "Newegg" in html
    assert "MicroCenter" in html
    assert "Amazon" in html
    assert "sortTable" in html
