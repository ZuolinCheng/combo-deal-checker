"""Micro Center bundle deal scraper."""
import asyncio
import re
import logging

from scrapers.base import BaseScraper
from config import Config
from models import ComboDeal, Component

logger = logging.getLogger(__name__)

MICROCENTER_BUNDLE_URLS = [
    "https://www.microcenter.com/site/content/bundle-and-save.aspx",
    "https://www.microcenter.com/site/content/intel-bundle-and-save.aspx",
]


def _parse_price(text: str) -> float:
    """Extract numeric price from a price string like '$799.97' or '1,249.99'."""
    if not text:
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def _detect_category(name: str) -> str:
    """Detect component category (cpu/motherboard/ram) from product name."""
    name_lower = name.lower()
    cpu_keywords = [
        "ryzen", "core i", "core ultra", "threadripper",
        "9800x3d", "9700x", "9600x", "9950x", "9900x",
        "7800x3d", "7700x", "7600x", "7950x", "7900x",
        "14900k", "14700k", "14600k", "13900k", "13700k", "13600k",
        "285k", "265k", "245k",
    ]
    if any(kw in name_lower for kw in cpu_keywords):
        return "cpu"
    mb_keywords = [
        "x870", "x670", "b850", "b650", "b550", "x570",
        "z790", "z690", "b760", "b660", "z890",
        "motherboard", "mainboard",
        "rog strix", "tuf gaming", "mag ", "aorus", "prime",
    ]
    if any(kw in name_lower for kw in mb_keywords):
        return "motherboard"
    ram_keywords = ["ddr5", "ddr4", "ram", "memory", "trident", "vengeance", "fury"]
    if any(kw in name_lower for kw in ram_keywords):
        return "ram"
    return "unknown"


def _parse_ram_specs(name: str) -> dict:
    """Extract DDR version, capacity (GB), and speed (MHz) from RAM name."""
    specs = {}
    name_lower = name.lower()
    ddr_match = re.search(r"ddr(\d)", name_lower)
    if ddr_match:
        specs["ddr"] = int(ddr_match.group(1))
    cap_match = re.search(r"(\d+)\s*gb", name_lower)
    if cap_match:
        specs["capacity_gb"] = int(cap_match.group(1))
    speed_match = re.search(r"ddr\d[- ]?(\d{4,5})", name_lower)
    if speed_match:
        specs["speed_mhz"] = int(speed_match.group(1))
    return specs


def _detect_combo_type(components: list[Component]) -> str:
    """Determine combo type from component categories."""
    categories = {c.category for c in components}
    has_cpu = "cpu" in categories
    has_mb = "motherboard" in categories
    has_ram = "ram" in categories
    if has_cpu and has_mb and has_ram:
        return "CPU+MB+RAM"
    if has_cpu and has_ram:
        return "CPU+RAM"
    if has_mb and has_ram:
        return "MB+RAM"
    if has_cpu and has_mb:
        return "CPU+MB"
    return "OTHER"


def parse_bundle_item(raw: dict) -> ComboDeal:
    """Parse a raw Micro Center bundle dict into a ComboDeal model.

    Args:
        raw: Dict with keys: title, price, url, components (list of dicts
             with name and optionally category).

    Returns:
        A populated ComboDeal instance.
    """
    components = []
    for comp_data in raw.get("components", []):
        name = comp_data.get("name", "")
        category = comp_data.get("category", "") or _detect_category(name)
        specs = {}
        if category == "ram":
            specs = _parse_ram_specs(name)
        components.append(Component(name=name, category=category, specs=specs))

    combo_type = _detect_combo_type(components)
    combo_price = _parse_price(raw.get("price", ""))

    deal = ComboDeal(
        retailer="MicroCenter",
        combo_type=combo_type,
        components=components,
        combo_price=combo_price,
        url=raw.get("url", ""),
    )

    cpu = deal.get_component("cpu")
    if cpu:
        deal.cpu_name = cpu.name
    mb = deal.get_component("motherboard")
    if mb:
        deal.motherboard_name = mb.name
    ram = deal.get_component("ram")
    if ram:
        deal.ram_name = ram.name
        deal.ram_speed_mhz = ram.specs.get("speed_mhz", 0)
        deal.ram_capacity_gb = ram.specs.get("capacity_gb", 0)

    return deal


class MicroCenterScraper(BaseScraper):
    """Scraper for Micro Center 3-in-1 bundle deals."""

    def __init__(self, config: Config):
        super().__init__(config)

    async def scrape(self) -> list[ComboDeal]:
        """Scrape Micro Center AMD and Intel bundle pages."""
        all_deals = []
        for url in MICROCENTER_BUNDLE_URLS:
            logger.info(f"[{self.retailer_name}] Navigating to {url}")
            await self._page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(5)
            await self._scroll_to_bottom()

            deals = await self._extract_bundle_deals()
            logger.info(f"[{self.retailer_name}] Found {len(deals)} deals from {url}")
            all_deals.extend(deals)
            await self._delay()

        return all_deals

    async def _extract_bundle_deals(self) -> list[ComboDeal]:
        """Extract bundle deals from the current page by parsing product links."""
        deals = []

        # Extract bundle product links with prices from the page
        bundles = await self._page.evaluate("""
            () => {
                const links = document.querySelectorAll('a[href*="/product/"]');
                const results = [];
                const seen = new Set();
                for (const a of links) {
                    const href = a.href || '';
                    if (!href.includes('bundle') && !href.includes('build-bundle')) continue;
                    if (seen.has(href)) continue;
                    seen.add(href);

                    // Walk up to find the price container
                    let container = a.closest('[id="Base"], [id="Upgrade"], .specs') || a.parentElement;
                    let priceEl = container ? container.querySelector('.price') : null;
                    let priceText = priceEl ? priceEl.textContent.trim() : '';

                    // Get the product name from the URL path
                    const pathMatch = href.match(/\\/product\\/\\d+\\/(.+)/);
                    let productPath = pathMatch ? pathMatch[1] : '';

                    // Also grab visible text for component names
                    let text = container ? container.textContent.replace(/\\s+/g, ' ').trim() : '';

                    results.push({
                        url: href,
                        productPath: productPath,
                        price: priceText,
                        text: text.substring(0, 500),
                    });
                }
                return results;
            }
        """)

        logger.info(f"[{self.retailer_name}] Found {len(bundles)} bundle links")

        for bundle in bundles:
            try:
                deal = self._parse_bundle_from_link(bundle)
                if deal and deal.combo_type != "OTHER":
                    deals.append(deal)
            except Exception as e:
                logger.warning(f"[{self.retailer_name}] Failed to parse bundle: {e}")

        return deals

    def _parse_bundle_from_link(self, bundle: dict) -> ComboDeal | None:
        """Parse a bundle deal from extracted link data."""
        url = bundle.get("url", "")
        price_text = bundle.get("price", "")
        product_path = bundle.get("productPath", "")
        page_text = bundle.get("text", "")

        combo_price = _parse_price(price_text)
        if combo_price <= 0:
            return None

        # Parse component names from URL path (comma-separated, hyphenated)
        # e.g. "amd-ryzen-7-9850x3d,-asus-x870-p-prime-wifi-am5,-gskill-flare-x5-series-32gb-ddr5-6000-kit,-computer-build-bundle"
        parts = product_path.replace("-computer-build-bundle", "").split(",-")
        components = []
        for part in parts:
            name = part.replace("-", " ").strip()
            if not name or len(name) < 3:
                continue
            category = _detect_category(name)
            specs = _parse_ram_specs(name) if category == "ram" else {}
            components.append(Component(name=name, category=category, specs=specs))

        if not components:
            return None

        combo_type = _detect_combo_type(components)
        deal = ComboDeal(
            retailer="MicroCenter",
            combo_type=combo_type,
            components=components,
            combo_price=combo_price,
            url=url,
        )

        cpu = deal.get_component("cpu")
        if cpu:
            deal.cpu_name = cpu.name
        mb = deal.get_component("motherboard")
        if mb:
            deal.motherboard_name = mb.name
        ram = deal.get_component("ram")
        if ram:
            deal.ram_name = ram.name
            deal.ram_speed_mhz = ram.specs.get("speed_mhz", 0)
            deal.ram_capacity_gb = ram.specs.get("capacity_gb", 0)

        return deal
