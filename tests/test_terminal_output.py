# tests/test_terminal_output.py
from output.terminal import render_deals_table
from models import ComboDeal, Component


def test_render_deals_table_returns_string():
    deals = [
        ComboDeal(
            retailer="Newegg",
            combo_type="CPU+MB+RAM",
            components=[
                Component("Ryzen 9 9900X", "cpu", {"cores": 12, "threads": 24}),
                Component("ASUS X870E", "motherboard", {}),
                Component("32GB DDR5-6000", "ram", {"ddr": 5, "capacity_gb": 32, "speed_mhz": 6000}),
            ],
            combo_price=879.0,
            individual_total=1050.0,
            savings=171.0,
            url="https://newegg.com/deal/123",
            cpu_name="Ryzen 9 9900X",
            cpu_cores="12C/24T",
            cpu_sc_score=4500,
            cpu_mc_score=52000,
            motherboard_name="ASUS X870E",
            ram_name="32GB DDR5-6000",
            ram_speed_mhz=6000,
            ram_capacity_gb=32,
        )
    ]
    output = render_deals_table(deals)
    assert "Newegg" in output
    assert "879" in output


def test_render_empty_deals():
    output = render_deals_table([])
    assert "No deals found" in output
