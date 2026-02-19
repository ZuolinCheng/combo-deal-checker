# tests/test_notifications.py
from models import ComboDeal, Component
from notifications import find_expired_deals


def _make_deal(url="https://www.newegg.com/combo/1", in_stock=True, combo_price=800.0):
    deal = ComboDeal(
        retailer="Newegg",
        combo_type="CPU+MB+RAM",
        components=[
            Component(name="Test CPU", category="cpu"),
            Component(name="Test MB", category="motherboard"),
            Component(name="Test RAM", category="ram", specs={"ddr": 5, "capacity_gb": 32}),
        ],
        combo_price=combo_price,
        url=url,
    )
    deal.in_stock = in_stock
    return deal


def test_find_expired_oos_deal():
    """OOS deal that was previously seen should be flagged."""
    oos = _make_deal(url="https://www.newegg.com/combo/1", in_stock=False)
    seen = {"https://www.newegg.com/combo/1"}
    scraper_results = {"NeweggScraper": {"status": "ok", "count": 1}}

    oos_deals, disappeared = find_expired_deals([oos], [], seen, scraper_results)
    assert len(oos_deals) == 1
    assert oos_deals[0].url == "https://www.newegg.com/combo/1"
    assert len(disappeared) == 0


def test_find_expired_oos_not_previously_seen():
    """OOS deal that was never seen before should NOT be flagged."""
    oos = _make_deal(url="https://www.newegg.com/combo/new", in_stock=False)
    seen = set()  # never seen before
    scraper_results = {"NeweggScraper": {"status": "ok", "count": 1}}

    oos_deals, disappeared = find_expired_deals([oos], [], seen, scraper_results)
    assert len(oos_deals) == 0


def test_find_expired_disappeared_deal():
    """Deal in seen_urls but not in any scraper result should be flagged."""
    in_stock = _make_deal(url="https://www.newegg.com/combo/2")
    seen = {
        "https://www.newegg.com/combo/2",  # still active
        "https://www.newegg.com/combo/99",  # disappeared
    }
    scraper_results = {"NeweggScraper": {"status": "ok", "count": 1}}

    oos_deals, disappeared = find_expired_deals([in_stock], [], seen, scraper_results)
    assert len(oos_deals) == 0
    assert "https://www.newegg.com/combo/99" in disappeared


def test_find_expired_disappeared_ignored_if_scraper_failed():
    """Disappeared deals should NOT be flagged if the scraper failed."""
    seen = {"https://www.newegg.com/combo/99"}
    scraper_results = {"NeweggScraper": {"status": "error", "error": "timeout"}}

    oos_deals, disappeared = find_expired_deals([], [], seen, scraper_results)
    assert len(disappeared) == 0


def test_find_expired_no_false_positive_for_active_deals():
    """Active, in-stock deals should never appear in either list."""
    active = _make_deal(url="https://www.newegg.com/combo/5", in_stock=True)
    seen = {"https://www.newegg.com/combo/5"}
    scraper_results = {"NeweggScraper": {"status": "ok", "count": 1}}

    oos_deals, disappeared = find_expired_deals([active], [], seen, scraper_results)
    assert len(oos_deals) == 0
    assert len(disappeared) == 0
