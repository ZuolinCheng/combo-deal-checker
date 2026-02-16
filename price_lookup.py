"""Amazon individual price lookup for calculating combo deal savings."""
import re
import asyncio
import logging

logger = logging.getLogger(__name__)


class AmazonPriceLookup:
    def __init__(self, config):
        self.config = config
        self._cache = {}

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
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("Playwright not installed; skipping price lookup")
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

            for deal in deals:
                for component in deal.components:
                    if component.individual_price > 0:
                        continue

                    if component.name in self._cache:
                        component.individual_price = self._cache[component.name]
                        continue

                    price = await self._search_price(page, component.name)
                    component.individual_price = price
                    self._cache[component.name] = price

                    # Respectful delay between requests
                    await asyncio.sleep(self.config.min_delay)

                deal.calculate_savings()

            await browser.close()

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
