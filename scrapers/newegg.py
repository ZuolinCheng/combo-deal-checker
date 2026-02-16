"""Newegg combo deal scraper."""
import re
import logging

from scrapers.base import BaseScraper
from config import Config
from models import ComboDeal, Component

logger = logging.getLogger(__name__)

NEWEGG_COMBO_URL = "https://www.newegg.com/combo-deals/category/id-1"


def _parse_price(text: str) -> float:
    """Extract numeric price from a price string like '$899.99' or '1,249.99'."""
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
    # CPU patterns
    cpu_keywords = [
        "ryzen", "core i", "core ultra", "threadripper",
        "9800x3d", "9700x", "9600x", "9950x", "9900x",
        "7800x3d", "7700x", "7600x", "7950x", "7900x",
        "14900k", "14700k", "14600k", "13900k", "13700k", "13600k",
        "285k", "265k", "245k",
    ]
    if any(kw in name_lower for kw in cpu_keywords):
        return "cpu"
    # Motherboard patterns
    mb_keywords = [
        "x870", "x670", "b850", "b650", "b550", "x570",
        "z790", "z690", "b760", "b660", "z890",
        "motherboard", "mainboard",
        "rog strix", "tuf gaming", "mag ", "aorus", "prime",
    ]
    if any(kw in name_lower for kw in mb_keywords):
        return "motherboard"
    # RAM patterns
    ram_keywords = ["ddr5", "ddr4", "ram", "memory", "trident", "vengeance", "fury"]
    if any(kw in name_lower for kw in ram_keywords):
        return "ram"
    return "unknown"


def _parse_ram_specs(name: str) -> dict:
    """Extract DDR version, capacity (GB), and speed (MHz) from RAM name."""
    specs = {}
    name_lower = name.lower()
    # DDR version
    ddr_match = re.search(r"ddr(\d)", name_lower)
    if ddr_match:
        specs["ddr"] = int(ddr_match.group(1))
    # Capacity in GB
    cap_match = re.search(r"(\d+)\s*gb", name_lower)
    if cap_match:
        specs["capacity_gb"] = int(cap_match.group(1))
    # Speed in MHz
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


def parse_combo_item(raw: dict) -> ComboDeal:
    """Parse a raw combo deal dict into a ComboDeal model.

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
        retailer="Newegg",
        combo_type=combo_type,
        components=components,
        combo_price=combo_price,
        url=raw.get("url", ""),
    )

    # Populate enriched fields
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


class NeweggScraper(BaseScraper):
    """Scraper for Newegg combo deals."""

    def __init__(self, config: Config):
        super().__init__(config)

    async def scrape(self) -> list[ComboDeal]:
        """Navigate to Newegg combo deals page, scroll and parse items."""
        logger.info(f"[{self.retailer_name}] Navigating to {NEWEGG_COMBO_URL}")
        await self._page.goto(NEWEGG_COMBO_URL, wait_until="networkidle")
        await self._delay()
        await self._scroll_to_bottom()

        deals = []
        # Extract combo deal items from the page
        items = await self._page.query_selector_all(".combo-item, .item-cell")
        logger.info(f"[{self.retailer_name}] Found {len(items)} raw items on page")

        for item in items:
            try:
                raw = await self._extract_combo_item(item)
                if raw:
                    deal = parse_combo_item(raw)
                    deals.append(deal)
            except Exception as e:
                logger.warning(f"[{self.retailer_name}] Failed to parse item: {e}")
                continue

        return deals

    async def _extract_combo_item(self, element) -> dict | None:
        """Extract raw combo deal data from a page element."""
        title_el = await element.query_selector(".combo-title, .item-title a")
        price_el = await element.query_selector(".price-current, .price")
        link_el = await element.query_selector("a.combo-title, .item-title a")

        if not title_el or not price_el:
            return None

        title = (await title_el.inner_text()).strip()
        price_text = (await price_el.inner_text()).strip()
        url = await link_el.get_attribute("href") if link_el else ""

        # Parse components from the title (split by + or ,)
        comp_names = re.split(r"\s*[+,]\s*", title)
        components = []
        for name in comp_names:
            name = name.strip()
            if name:
                category = _detect_category(name)
                components.append({"name": name, "category": category})

        return {
            "title": title,
            "price": price_text,
            "url": url or "",
            "components": components,
        }
