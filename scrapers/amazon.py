"""Amazon combo/bundle deal scraper."""
import re
import logging

from scrapers.base import BaseScraper
from config import Config
from models import ComboDeal, Component

logger = logging.getLogger(__name__)

AMAZON_SEARCH_QUERIES = [
    "CPU motherboard RAM combo",
    "processor motherboard memory bundle",
    "AMD Ryzen motherboard RAM combo",
    "Intel Core motherboard RAM combo",
    "motherboard RAM combo",
    "motherboard memory bundle",
    "CPU RAM combo",
    "processor memory bundle",
]


def _parse_price(text: str) -> float:
    """Extract numeric price from a price string like '$849.99' or '1,249.99'."""
    if not text:
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def lookup_individual_price_from_text(text: str) -> float:
    """Parse a price string into a float value.

    Args:
        text: Price string like '$449.99', '449.99', or '$1,249.99'.

    Returns:
        Float price value, or 0.0 if unparseable.
    """
    return _parse_price(text)


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


def parse_amazon_result(raw: dict) -> ComboDeal:
    """Parse a raw Amazon search result dict into a ComboDeal model.

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
        retailer="Amazon",
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


class AmazonScraper(BaseScraper):
    """Scraper for Amazon combo/bundle deals.

    Searches multiple queries and deduplicates results by URL.
    """

    def __init__(self, config: Config):
        super().__init__(config)

    async def scrape(self) -> list[ComboDeal]:
        """Search Amazon for combo deals using multiple queries."""
        seen_urls = set()
        deals = []

        for query in AMAZON_SEARCH_QUERIES:
            try:
                query_deals = await self._search_query(query)
                for deal in query_deals:
                    if deal.url and deal.url not in seen_urls:
                        seen_urls.add(deal.url)
                        deals.append(deal)
            except Exception as e:
                logger.warning(
                    f"[{self.retailer_name}] Query '{query}' failed: {e}"
                )
                continue
            await self._delay()

        logger.info(
            f"[{self.retailer_name}] Found {len(deals)} unique deals "
            f"from {len(AMAZON_SEARCH_QUERIES)} queries"
        )
        return deals

    async def _search_query(self, query: str) -> list[ComboDeal]:
        """Execute a single search query on Amazon."""
        search_url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
        logger.info(f"[{self.retailer_name}] Searching: {search_url}")
        await self._page.goto(search_url, wait_until="domcontentloaded")
        await self._delay()
        await self._scroll_to_bottom()

        results = []
        items = await self._page.query_selector_all(
            "[data-component-type='s-search-result']"
        )

        for item in items:
            try:
                raw = await self._extract_result(item)
                if raw:
                    deal = parse_amazon_result(raw)
                    results.append(deal)
            except Exception as e:
                logger.warning(
                    f"[{self.retailer_name}] Failed to parse result: {e}"
                )
                continue

        return results

    async def _extract_result(self, element) -> dict | None:
        """Extract raw deal data from a search result element."""
        title_el = await element.query_selector(
            "h2 a span, .a-text-normal"
        )
        price_whole = await element.query_selector(".a-price-whole")
        price_frac = await element.query_selector(".a-price-fraction")
        link_el = await element.query_selector("h2 a")

        if not title_el or not price_whole:
            return None

        title = (await title_el.inner_text()).strip()
        whole = (await price_whole.inner_text()).strip().rstrip(".")
        frac = (await price_frac.inner_text()).strip() if price_frac else "00"
        price_text = f"${whole}.{frac}"
        url = ""
        if link_el:
            href = await link_el.get_attribute("href")
            if href:
                url = (
                    f"https://www.amazon.com{href}"
                    if href.startswith("/")
                    else href
                )

        # Parse components from the title
        comp_names = re.split(r"\s*[+,]\s*", title)
        components = []
        for name in comp_names:
            name = name.strip()
            if name:
                category = _detect_category(name)
                components.append({"name": name, "category": category})

        if not components:
            return None

        return {
            "title": title,
            "price": price_text,
            "url": url,
            "components": components,
        }
