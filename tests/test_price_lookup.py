# tests/test_price_lookup.py
from price_lookup import AmazonPriceLookup


def test_parse_price_from_text():
    lookup = AmazonPriceLookup.__new__(AmazonPriceLookup)
    assert lookup._parse_price("$449.99") == 449.99
    assert lookup._parse_price("$1,299.99") == 1299.99
    assert lookup._parse_price("") == 0.0
