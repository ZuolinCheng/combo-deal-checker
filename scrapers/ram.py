"""Standalone DDR5 RAM scrapers for all 4 retailers."""
import re
import logging

from scrapers.base import BaseScraper
from scrapers.newegg import _parse_ram_specs
from config import Config
from models import RAMDeal

logger = logging.getLogger(__name__)

TARGET_CAPACITIES = [48, 64, 96, 128]

# Non-RAM product keywords to filter out search noise
NON_RAM_KEYWORDS = [
    "laptop", "notebook", "monitor", "ssd", "nvme", "hard drive",
    "printer", "router", "keyboard", "mouse", "headset", "webcam",
    "case", "chassis", "power supply", "psu", "cooler", "fan",
    "gpu", "graphics card", "motherboard", "mainboard",
    "cpu", "processor", "intel core", "amd ryzen",
    "sodimm", "so-dimm",
]

RAM_BRAND_KEYWORDS = [
    "corsair", "g.skill", "gskill", "kingston", "crucial", "patriot",
    "v-color", "v color", "team", "mushkin", "pny", "silicon power",
    "oloy", "xpg", "adata",
]


def _parse_price(text: str) -> float:
    """Extract numeric price from text like '$189.99' or '1,249.99'."""
    if not text:
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def _is_likely_ram(name: str) -> bool:
    """Return True if the product name looks like a desktop DDR5 RAM kit."""
    lower = name.lower()
    has_ram_indicator = any(kw in lower for kw in [
        "ddr5", "memory", "ram", "dimm",
        "trident", "vengeance", "fury", "flare",
        "ripjaws", "dominator",
    ])
    if not has_ram_indicator:
        has_ram_indicator = any(kw in lower for kw in RAM_BRAND_KEYWORDS)

    has_non_ram = any(kw in lower for kw in NON_RAM_KEYWORDS)

    return has_ram_indicator and not has_non_ram


def _parse_ram_deal(name: str, price: float, url: str, retailer: str) -> RAMDeal | None:
    """Parse a product listing into a RAMDeal, or None if not valid RAM."""
    if not _is_likely_ram(name):
        return None

    specs = _parse_ram_specs(name)

    ddr = specs.get("ddr", 0)
    capacity = specs.get("capacity_gb", 0)
    speed = specs.get("speed_mhz", 0)

    # Must be DDR5
    if ddr != 5 and ddr != 0:
        return None
    if ddr == 0:
        if "ddr5" in name.lower():
            ddr = 5
        else:
            return None

    if capacity <= 0 or price <= 0:
        return None

    return RAMDeal(
        retailer=retailer,
        name=name,
        capacity_gb=capacity,
        speed_mhz=speed,
        ddr_version=ddr,
        price=price,
        url=url,
    )


class NeweggRAMScraper(BaseScraper):
    """Scrape standalone DDR5 RAM kits from Newegg."""

    async def scrape(self) -> list:
        seen_urls: set[str] = set()
        deals = []
        for capacity in TARGET_CAPACITIES:
            url = f"https://www.newegg.com/p/pl?d=ddr5+{capacity}gb+desktop+memory"
            logger.info(f"[{self.retailer_name}] Searching {capacity}GB: {url}")
            try:
                await self._page.goto(url, wait_until="domcontentloaded")
                await self._delay()
                await self._scroll_to_bottom()

                items = await self._page.query_selector_all(".item-cell")
                for item in items:
                    try:
                        raw = await self._extract_item(item)
                        if raw and raw["url"] not in seen_urls:
                            seen_urls.add(raw["url"])
                            deal = _parse_ram_deal(raw["name"], raw["price"], raw["url"], "Newegg")
                            if deal:
                                deals.append(deal)
                    except Exception as e:
                        logger.debug(f"[{self.retailer_name}] Failed to extract item: {e}")
            except Exception as e:
                logger.warning(f"[{self.retailer_name}] {capacity}GB search failed: {e}")
            await self._delay()

        logger.info(f"[{self.retailer_name}] Found {len(deals)} RAM deals")
        return deals

    async def _extract_item(self, element) -> dict | None:
        """Extract name, price, URL from a Newegg .item-cell element."""
        title_el = await element.query_selector(".item-title")
        price_el = await element.query_selector(".price-current")
        if not title_el or not price_el:
            return None
        name = (await title_el.inner_text()).strip()
        price_text = (await price_el.inner_text()).strip()
        url = await title_el.get_attribute("href") or ""
        if url.startswith("/"):
            url = f"https://www.newegg.com{url}"
        price = _parse_price(price_text)
        if not name or price <= 0:
            return None
        return {"name": name, "price": price, "url": url}


class AmazonRAMScraper(BaseScraper):
    """Scrape standalone DDR5 RAM kits from Amazon."""

    async def scrape(self) -> list:
        seen_urls: set[str] = set()
        deals = []
        for capacity in TARGET_CAPACITIES:
            query = f"ddr5+{capacity}gb+desktop+memory"
            url = f"https://www.amazon.com/s?k={query}"
            logger.info(f"[{self.retailer_name}] Searching {capacity}GB: {url}")
            try:
                await self._page.goto(url, wait_until="domcontentloaded")
                await self._delay()
                await self._scroll_to_bottom()

                items = await self._page.query_selector_all(
                    "[data-component-type='s-search-result']"
                )
                for item in items:
                    try:
                        raw = await self._extract_item(item)
                        if raw and raw["url"] not in seen_urls:
                            seen_urls.add(raw["url"])
                            deal = _parse_ram_deal(raw["name"], raw["price"], raw["url"], "Amazon")
                            if deal:
                                deals.append(deal)
                    except Exception as e:
                        logger.debug(f"[{self.retailer_name}] Failed to extract item: {e}")
            except Exception as e:
                logger.warning(f"[{self.retailer_name}] {capacity}GB search failed: {e}")
            await self._delay()

        logger.info(f"[{self.retailer_name}] Found {len(deals)} RAM deals")
        return deals

    async def _extract_item(self, element) -> dict | None:
        """Extract name, price, URL from an Amazon search result."""
        title_el = await element.query_selector("h2 span, h2 a span, .a-text-normal")
        price_whole = await element.query_selector(".a-price-whole")
        price_frac = await element.query_selector(".a-price-fraction")
        link_el = await element.query_selector("a.a-link-normal[href*='/dp/'], h2 a")

        if not title_el or not price_whole:
            return None

        name = (await title_el.inner_text()).strip()
        whole = (await price_whole.inner_text()).strip().rstrip(".")
        frac = (await price_frac.inner_text()).strip() if price_frac else "00"
        price = _parse_price(f"${whole}.{frac}")

        url = ""
        if link_el:
            href = await link_el.get_attribute("href")
            if href:
                url = f"https://www.amazon.com{href}" if href.startswith("/") else href

        if not name or price <= 0:
            return None
        return {"name": name, "price": price, "url": url}


class MicroCenterRAMScraper(BaseScraper):
    """Scrape standalone DDR5 RAM kits from Micro Center."""

    async def scrape(self) -> list:
        seen_urls: set[str] = set()
        deals = []
        # Broad "ddr5" search plus per-capacity searches for maximum coverage
        queries = ["ddr5"] + [f"ddr5+{cap}gb" for cap in TARGET_CAPACITIES]
        for query in queries:
            url = f"https://www.microcenter.com/search/search_results.aspx?Ntt={query}"
            logger.info(f"[{self.retailer_name}] Searching '{query}': {url}")
            try:
                await self._page.goto(url, wait_until="domcontentloaded")
                await self._delay()
                await self._scroll_to_bottom()

                items = await self._page.query_selector_all(".product_wrapper")
                for item in items:
                    try:
                        raw = await self._extract_item(item)
                        if raw and raw["url"] not in seen_urls:
                            seen_urls.add(raw["url"])
                            deal = _parse_ram_deal(raw["name"], raw["price"], raw["url"], "MicroCenter")
                            if deal:
                                deals.append(deal)
                    except Exception as e:
                        logger.debug(f"[{self.retailer_name}] Failed to extract item: {e}")
            except Exception as e:
                logger.warning(f"[{self.retailer_name}] '{query}' search failed: {e}")
            await self._delay()

        logger.info(f"[{self.retailer_name}] Found {len(deals)} RAM deals")
        return deals

    async def _extract_item(self, element) -> dict | None:
        """Extract name, price, URL from a Micro Center search result."""
        title_el = await element.query_selector(".pDescription a")
        price_attr = await element.query_selector("[data-price]")

        if not title_el:
            return None

        name = (await title_el.inner_text()).strip()
        href = await title_el.get_attribute("href") or ""
        url = f"https://www.microcenter.com{href}" if href.startswith("/") else href

        price = 0.0
        if price_attr:
            price_val = await price_attr.get_attribute("data-price") or ""
            price = _parse_price(price_val)

        if not name or price <= 0:
            return None
        return {"name": name, "price": price, "url": url}


class BHPhotoRAMScraper(BaseScraper):
    """Scrape standalone DDR5 RAM kits from B&H Photo."""

    async def scrape(self) -> list:
        seen_urls: set[str] = set()
        deals = []
        for capacity in TARGET_CAPACITIES:
            query = f"ddr5 {capacity}gb desktop memory"
            url = f"https://www.bhphotovideo.com/c/search?q={query.replace(' ', '%20')}"
            logger.info(f"[{self.retailer_name}] Searching {capacity}GB: {url}")
            try:
                await self._page.goto(url, wait_until="domcontentloaded")
                await self._delay()
                await self._scroll_to_bottom()

                items = await self._page.query_selector_all(
                    "[data-selenium='miniProductPage'], .product-item"
                )
                for item in items:
                    try:
                        raw = await self._extract_item(item)
                        if raw and raw["url"] not in seen_urls:
                            seen_urls.add(raw["url"])
                            deal = _parse_ram_deal(raw["name"], raw["price"], raw["url"], "BHPhoto")
                            if deal:
                                deals.append(deal)
                    except Exception as e:
                        logger.debug(f"[{self.retailer_name}] Failed to extract item: {e}")
            except Exception as e:
                logger.warning(f"[{self.retailer_name}] {capacity}GB search failed: {e}")
            await self._delay()

        logger.info(f"[{self.retailer_name}] Found {len(deals)} RAM deals")
        return deals

    async def _extract_item(self, element) -> dict | None:
        """Extract name, price, URL from a B&H Photo search result."""
        title_el = await element.query_selector(
            "[data-selenium='miniProductPageProductName'], .product-title a"
        )
        price_el = await element.query_selector(
            "[data-selenium='uppedDecimalPriceFirst'], .price"
        )
        link_el = await element.query_selector(
            "[data-selenium='miniProductPageProductName'] a, .product-title a"
        )

        if not title_el or not price_el:
            return None

        name = (await title_el.inner_text()).strip()
        price_text = (await price_el.inner_text()).strip()
        price = _parse_price(price_text)

        url = ""
        if link_el:
            href = await link_el.get_attribute("href") or ""
            url = f"https://www.bhphotovideo.com{href}" if href.startswith("/") else href

        if not name or price <= 0:
            return None
        return {"name": name, "price": price, "url": url}
