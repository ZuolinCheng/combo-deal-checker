# tests/test_ram_filters.py
from models import RAMDeal
from ram_filters import (
    check_ram_capacity, check_ram_ddr5, check_ram_price,
    filter_ram_deals, RAM_PRICE_LIMITS,
)


def _make_ram_deal(capacity_gb=64, price=189.99, speed_mhz=6000, ddr=5, retailer="Newegg"):
    return RAMDeal(
        retailer=retailer,
        name=f"Test RAM {capacity_gb}GB",
        capacity_gb=capacity_gb,
        speed_mhz=speed_mhz,
        ddr_version=ddr,
        price=price,
    )


def test_check_capacity_valid_48():
    assert check_ram_capacity(_make_ram_deal(capacity_gb=48)) is True


def test_check_capacity_valid_64():
    assert check_ram_capacity(_make_ram_deal(capacity_gb=64)) is True


def test_check_capacity_valid_96():
    assert check_ram_capacity(_make_ram_deal(capacity_gb=96)) is True


def test_check_capacity_valid_128():
    assert check_ram_capacity(_make_ram_deal(capacity_gb=128)) is True


def test_check_capacity_rejects_32():
    """32GB is explicitly excluded — must be > 32GB."""
    assert check_ram_capacity(_make_ram_deal(capacity_gb=32)) is False


def test_check_capacity_rejects_16():
    assert check_ram_capacity(_make_ram_deal(capacity_gb=16)) is False


def test_check_capacity_rejects_24():
    assert check_ram_capacity(_make_ram_deal(capacity_gb=24)) is False


def test_check_ddr5_passes():
    assert check_ram_ddr5(_make_ram_deal(ddr=5)) is True


def test_check_ddr5_rejects_ddr4():
    assert check_ram_ddr5(_make_ram_deal(ddr=4)) is False


def test_check_price_48gb_within_limit():
    assert check_ram_price(_make_ram_deal(capacity_gb=48, price=400.0)) is True


def test_check_price_64gb_at_limit():
    assert check_ram_price(_make_ram_deal(capacity_gb=64, price=650.0)) is True


def test_check_price_64gb_over_limit():
    assert check_ram_price(_make_ram_deal(capacity_gb=64, price=651.0)) is False


def test_check_price_96gb_within_limit():
    assert check_ram_price(_make_ram_deal(capacity_gb=96, price=700.0)) is True


def test_check_price_128gb_at_limit():
    assert check_ram_price(_make_ram_deal(capacity_gb=128, price=800.0)) is True


def test_check_price_128gb_over_limit():
    assert check_ram_price(_make_ram_deal(capacity_gb=128, price=801.0)) is False


def test_check_price_rejects_zero():
    assert check_ram_price(_make_ram_deal(capacity_gb=64, price=0.0)) is False


def test_filter_ram_deals_integration():
    deals = [
        _make_ram_deal(capacity_gb=64, price=189.99),
        _make_ram_deal(capacity_gb=32, price=99.99),      # capacity too small
        _make_ram_deal(capacity_gb=64, price=750.0),       # over $650 limit
        _make_ram_deal(capacity_gb=96, price=399.99),
        _make_ram_deal(capacity_gb=128, price=799.99),
        _make_ram_deal(capacity_gb=64, price=189.99, ddr=4),  # DDR4
    ]
    filtered = filter_ram_deals(deals)
    assert len(filtered) == 3
    capacities = {d.capacity_gb for d in filtered}
    assert capacities == {64, 96, 128}


def test_filter_sorted_by_savings_then_speed():
    deals = [
        _make_ram_deal(capacity_gb=64, price=180.0, speed_mhz=6000),
        _make_ram_deal(capacity_gb=64, price=180.0, speed_mhz=7200),
    ]
    deals[0].savings = 20.0
    deals[1].savings = 20.0
    filtered = filter_ram_deals(deals)
    assert filtered[0].speed_mhz == 7200  # same savings, higher speed first
