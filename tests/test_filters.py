# tests/test_filters.py
from filters import filter_deals, check_ddr5, check_ram_capacity, check_budget
from models import ComboDeal, Component
from config import Config


def _make_deal(ram_specs=None, combo_price=800.0):
    """Helper to create a test deal."""
    ram_specs = ram_specs or {"ddr": 5, "capacity_gb": 32, "speed_mhz": 6000}
    return ComboDeal(
        retailer="TestRetailer",
        combo_type="CPU+MB+RAM",
        components=[
            Component(name="Test CPU", category="cpu", specs={"socket": "AM5"}),
            Component(name="Test MB", category="motherboard", specs={}),
            Component(name="Test RAM", category="ram", specs=ram_specs),
        ],
        combo_price=combo_price,
        url="https://example.com",
    )


def test_check_ddr5_passes():
    deal = _make_deal(ram_specs={"ddr": 5, "capacity_gb": 32})
    assert check_ddr5(deal) is True


def test_check_ddr5_rejects_ddr4():
    deal = _make_deal(ram_specs={"ddr": 4, "capacity_gb": 32})
    assert check_ddr5(deal) is False


def test_check_ram_capacity_passes():
    deal = _make_deal(ram_specs={"ddr": 5, "capacity_gb": 64})
    assert check_ram_capacity(deal, min_gb=32) is True


def test_check_ram_capacity_rejects_small():
    deal = _make_deal(ram_specs={"ddr": 5, "capacity_gb": 16})
    assert check_ram_capacity(deal, min_gb=32) is False


def test_check_budget_in_range():
    deal = _make_deal(combo_price=700.0)
    assert check_budget(deal, 500, 1300) is True


def test_check_budget_too_low():
    deal = _make_deal(combo_price=300.0)
    assert check_budget(deal, 500, 1300) is False


def test_check_budget_too_high():
    deal = _make_deal(combo_price=1500.0)
    assert check_budget(deal, 500, 1300) is False


def test_filter_deals_removes_out_of_stock():
    config = Config()
    in_stock = _make_deal(ram_specs={"ddr": 5, "capacity_gb": 32}, combo_price=800)
    out_of_stock = _make_deal(ram_specs={"ddr": 5, "capacity_gb": 32}, combo_price=750)
    out_of_stock.in_stock = False
    filtered = filter_deals([in_stock, out_of_stock], config)
    assert len(filtered) == 1
    assert filtered[0].combo_price == 800


def test_filter_deals_integration():
    config = Config()
    deals = [
        _make_deal(ram_specs={"ddr": 5, "capacity_gb": 32}, combo_price=800),
        _make_deal(ram_specs={"ddr": 4, "capacity_gb": 32}, combo_price=600),  # DDR4
        _make_deal(ram_specs={"ddr": 5, "capacity_gb": 16}, combo_price=700),  # <32GB
        _make_deal(ram_specs={"ddr": 5, "capacity_gb": 64}, combo_price=2200), # over budget
    ]
    filtered = filter_deals(deals, config)
    assert len(filtered) == 1
    assert filtered[0].combo_price == 800
