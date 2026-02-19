"""Base scraper class with shared Playwright browser logic."""
import logging
import random
import asyncio
from abc import ABC, abstractmethod

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import Config

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    def __init__(self, config: Config):
        self.config = config
        self.retailer_name = self.__class__.__name__
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def _get_random_delay(self) -> float:
        return random.uniform(self.config.min_delay, self.config.max_delay)

    async def _delay(self):
        delay = self._get_random_delay()
        logger.debug(f"[{self.retailer_name}] Waiting {delay:.1f}s")
        await asyncio.sleep(delay)

    async def _launch_browser(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.headless
        )
        self._context = await self._browser.new_context(
            viewport={
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            },
            user_agent=self.config.user_agent,
        )
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.config.request_timeout)

    async def _close_browser(self):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def _scroll_to_bottom(self):
        """Scroll page to load lazy-loaded content."""
        prev_height = 0
        while True:
            curr_height = await self._page.evaluate("document.body.scrollHeight")
            if curr_height == prev_height:
                break
            prev_height = curr_height
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self._delay()

    async def run(self) -> list:
        """Run the scraper with retry logic."""
        for attempt in range(1, self.config.max_retries + 1):
            try:
                logger.info(f"[{self.retailer_name}] Attempt {attempt}/{self.config.max_retries}")
                await self._launch_browser()
                deals = await self.scrape()
                logger.info(f"[{self.retailer_name}] Found {len(deals)} deals")
                return deals
            except Exception as e:
                logger.warning(f"[{self.retailer_name}] Attempt {attempt} failed: {e}")
                if attempt < self.config.max_retries:
                    wait = self.config.retry_backoff ** attempt
                    logger.info(f"[{self.retailer_name}] Retrying in {wait:.0f}s")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"[{self.retailer_name}] All attempts failed")
                    return []
            finally:
                await self._close_browser()

    @abstractmethod
    async def scrape(self) -> list:
        """Scrape combo deals. Implemented by each retailer."""
        ...
