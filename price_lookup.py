"""Amazon individual price lookup for calculating combo deal savings."""
import re
import asyncio
import logging

from cache import DealCache

logger = logging.getLogger(__name__)


class AmazonPriceLookup:
    def __init__(self, config, cache: DealCache | None = None):
        self.config = config
        self._cache = {}  # in-memory per-run cache
        self._disk_cache = cache  # persistent cross-run cache

    def _parse_price(self, text: str) -> float:
        """Extract a float price from text like '$449.99' or '$1,299.99'."""
        if not text:
            return 0.0
        match = re.search(r'[\$]?([\d,]+\.?\d*)', text)
        if match:
            price_str = match.group(1).replace(',', '')
            try:
                return float(price_str)
            except ValueError:
                return 0.0
        return 0.0

    async def lookup_prices(self, deals):
        """Look up individual Amazon prices for each component missing a price.

        For each component in each deal that has no individual_price set,
        searches Amazon for the product and sets the price. After all
        components are priced, recalculates deal savings.

        Results are cached by component name to avoid duplicate lookups.
        Uses persistent disk cache (8h TTL) to skip lookups across runs.
        """
        # Phase 1: Resolve as many prices as possible from the disk cache
        needs_lookup = []
        cache_hits = 0
        for deal in deals:
            for component in deal.components:
                if component.individual_price > 0:
                    continue
                if component.category == "unknown":
                    continue
                if component.name in self._cache:
                    component.individual_price = self._cache[component.name]
                    continue
                # Check persistent disk cache
                if self._disk_cache:
                    cached_price = self._disk_cache.load_amazon_price(component.name)
                    if cached_price is not None:
                        component.individual_price = cached_price
                        self._cache[component.name] = cached_price
                        cache_hits += 1
                        continue
                needs_lookup.append(component)

        if cache_hits:
            logger.info(f"Amazon price cache: {cache_hits} hits from disk cache")

        # Phase 2: Only launch a browser if there are uncached components
        if needs_lookup:
            unique_names = set()
            deduplicated = []
            for comp in needs_lookup:
                if comp.name not in unique_names:
                    unique_names.add(comp.name)
                    deduplicated.append(comp)

            logger.info(f"Amazon price lookup: {len(deduplicated)} unique components to look up")

            try:
                from playwright.async_api import async_playwright
            except ImportError:
                logger.warning("Playwright not installed; skipping price lookup")
                for deal in deals:
                    deal.calculate_savings()
                return deals

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.config.headless)
                context = await browser.new_context(
                    viewport={
                        "width": self.config.viewport_width,
                        "height": self.config.viewport_height,
                    },
                    user_agent=self.config.user_agent,
                )
                page = await context.new_page()

                for component in deduplicated:
                    price = await self._search_price(page, component.name)
                    self._cache[component.name] = price
                    if self._disk_cache:
                        self._disk_cache.save_amazon_price(component.name, price)
                    await asyncio.sleep(self.config.min_delay)

                await browser.close()

            # Apply looked-up prices to all components (including duplicates)
            for deal in deals:
                for component in deal.components:
                    if component.individual_price <= 0 and component.name in self._cache:
                        component.individual_price = self._cache[component.name]
        else:
            logger.info("Amazon price lookup: all prices cached, skipping browser launch")

        for deal in deals:
            deal.calculate_savings()

        return deals

    async def _search_price(self, page, product_name: str) -> float:
        """Search Amazon for a product and return the first result's price."""
        search_url = f"https://www.amazon.com/s?k={product_name.replace(' ', '+')}"
        try:
            await page.goto(search_url, timeout=self.config.request_timeout)
            # Wait for search results
            await page.wait_for_selector(
                '[data-component-type="s-search-result"]',
                timeout=self.config.request_timeout,
            )
            # Get the first result's price
            price_element = await page.query_selector(
                '[data-component-type="s-search-result"] .a-price .a-offscreen'
            )
            if price_element:
                price_text = await price_element.inner_text()
                return self._parse_price(price_text)
        except Exception as e:
            logger.warning(f"Failed to look up price for '{product_name}': {e}")
        return 0.0
