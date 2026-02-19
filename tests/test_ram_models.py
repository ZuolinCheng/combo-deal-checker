# tests/test_ram_models.py
from models import RAMDeal


def test_ram_deal_defaults():
    deal = RAMDeal(retailer="Newegg", name="Test RAM")
    assert deal.ddr_version == 5
    assert deal.price == 0.0
    assert deal.amazon_price == 0.0
    assert deal.savings == 0.0
    assert deal.capacity_gb == 0
    assert deal.speed_mhz == 0


def test_ram_deal_with_values():
    deal = RAMDeal(
        retailer="Newegg",
        name="G.SKILL 64GB DDR5-6000",
        capacity_gb=64,
        speed_mhz=6000,
        price=189.99,
        amazon_price=219.99,
        savings=30.0,
    )
    assert deal.capacity_gb == 64
    assert deal.speed_mhz == 6000
    assert deal.price == 189.99
    assert deal.amazon_price == 219.99
    assert deal.savings == 30.0


def test_ram_deal_amazon_self_reference():
    """Amazon deals have savings=0 since price IS the Amazon price."""
    deal = RAMDeal(
        retailer="Amazon",
        name="Kingston 64GB DDR5-6000",
        price=209.99,
        amazon_price=209.99,
        savings=0.0,
    )
    assert deal.savings == 0.0
    assert deal.retailer == "Amazon"


def test_ram_deal_timestamp_auto():
    deal = RAMDeal(retailer="Newegg", name="Test")
    assert deal.timestamp  # auto-populated
