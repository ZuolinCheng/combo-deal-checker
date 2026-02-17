"""Cache layer for combo deal checker — avoids redundant browser visits."""
import json
import logging
import os
import time

logger = logging.getLogger(__name__)


class DealCache:
    """Manages JSON-file caches for Amazon prices and deal detail pages."""

    def __init__(self, cache_dir: str = "cache", price_ttl: int = 28800):
        self.cache_dir = cache_dir
        self.price_ttl = price_ttl  # seconds (default 8h)
        self._prices_file = os.path.join(cache_dir, "amazon_prices.json")
        self._details_file = os.path.join(cache_dir, "deal_details.json")
        self._prices: dict = {}
        self._details: dict = {}
        self._load()

    def _load(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        self._prices = self._read_json(self._prices_file)
        self._details = self._read_json(self._details_file)
        logger.info(
            f"Cache loaded: {len(self._prices)} prices, {len(self._details)} deal details"
        )

    def _read_json(self, path: str) -> dict:
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read cache {path}: {e}")
            return {}

    def _write_json(self, path: str, data: dict):
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            logger.warning(f"Failed to write cache {path}: {e}")

    def save(self):
        """Persist all caches to disk."""
        self._write_json(self._prices_file, self._prices)
        self._write_json(self._details_file, self._details)

    # --- Amazon price cache (8h TTL) ---

    def load_amazon_price(self, component_name: str) -> float | None:
        """Return cached price if fresh, else None."""
        entry = self._prices.get(component_name)
        if not entry:
            return None
        age = time.time() - entry.get("timestamp", 0)
        if age > self.price_ttl:
            return None
        return entry.get("price")

    def save_amazon_price(self, component_name: str, price: float):
        self._prices[component_name] = {
            "price": price,
            "timestamp": time.time(),
        }

    # --- Deal detail cache (no expiry) ---

    def load_deal_detail(self, url: str) -> dict | None:
        """Return cached detail-page data for a deal URL, or None."""
        return self._details.get(url)

    def save_deal_detail(self, url: str, detail: dict):
        self._details[url] = detail

    def clear(self):
        """Clear all cached data (for --fresh)."""
        self._prices = {}
        self._details = {}
        self.save()
        logger.info("Cache cleared")
