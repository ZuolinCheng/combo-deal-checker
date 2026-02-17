"""Newegg combo deal scraper."""
import re
import logging

from scrapers.base import BaseScraper
from config import Config
from models import ComboDeal, Component

logger = logging.getLogger(__name__)

NEWEGG_BASE_URL = "https://www.newegg.com"
NEWEGG_SEARCH_URLS = [
    "https://www.newegg.com/p/pl?d=cpu+motherboard+ram+combo+ddr5",
    "https://www.newegg.com/p/pl?d=cpu+motherboard+ram+bundle",
]
MAX_PAGES = 10  # safety limit


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
        "9850x3d", "9800x3d", "9700x", "9600x", "9950x", "9900x",
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
    # RAM patterns — include brand SKU prefixes for truncated titles
    ram_keywords = [
        "ddr5", "ddr4", "ram", "memory", "trident", "vengeance", "fury",
        "corsair cmh", "corsair cmk", "v-color", "v color", "tmxs",
        "team group", "ff3d", "kingston fury", "gskill", "g.skill",
    ]
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
    # Capacity in GB — handle kit formats like "2x16GB" or "2 x 16GB"
    kit_match = re.search(r"(\d+)\s*x\s*(\d+)\s*gb", name_lower)
    if kit_match:
        sticks = int(kit_match.group(1))
        per_stick = int(kit_match.group(2))
        specs["capacity_gb"] = sticks * per_stick
    else:
        cap_match = re.search(r"(\d+)\s*gb", name_lower)
        if cap_match:
            specs["capacity_gb"] = int(cap_match.group(1))
    # Speed in MHz
    speed_match = re.search(r"ddr\d[- ]?(\d{4,5})", name_lower)
    if speed_match:
        specs["speed_mhz"] = int(speed_match.group(1))
    return specs


def _extract_prefix_categories(title: str) -> list[str]:
    """Extract component category order from a Newegg combo title prefix.

    E.g. "CPU Motherboard Memory Combo - ..." → ["cpu", "motherboard", "ram"]
         "Motherboard CPU Memory Combo - ..." → ["motherboard", "cpu", "ram"]
    """
    prefix_match = re.match(
        r"^((?:CPU|Motherboard|Memory|Combo|Bundle)(?:\s+(?:CPU|Motherboard|Memory|Combo|Bundle))*)\s*[-–—]",
        title, flags=re.IGNORECASE,
    )
    if not prefix_match:
        return []
    words = prefix_match.group(1).split()
    category_map = {"cpu": "cpu", "motherboard": "motherboard", "memory": "ram"}
    return [category_map[w.lower()] for w in words if w.lower() in category_map]


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
            # Newegg search is DDR5-only; infer DDR5 if not found in abbreviated name
            if "ddr" not in specs:
                specs["ddr"] = 5
        components.append(Component(name=name, category=category, specs=specs))

    combo_type = _detect_combo_type(components)
    combo_price = _parse_price(raw.get("price", ""))

    url = raw.get("url", "")
    if url and url.startswith("/"):
        url = NEWEGG_BASE_URL + url

    deal = ComboDeal(
        retailer="Newegg",
        combo_type=combo_type,
        components=components,
        combo_price=combo_price,
        url=url,
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
        """Search Newegg for CPU+MB+RAM combo deals across multiple queries and pages."""
        # Phase 1: Collect all raw items from search pages without navigating away.
        # Element handles become stale if we navigate, so extract all data first.
        all_raw_items: list[dict] = []
        seen_urls: set[str] = set()

        for search_url in NEWEGG_SEARCH_URLS:
            logger.info(f"[{self.retailer_name}] Starting search: {search_url}")
            for page_num in range(1, MAX_PAGES + 1):
                page_url = search_url if page_num == 1 else f"{search_url}&page={page_num}"
                logger.info(f"[{self.retailer_name}] Navigating to {page_url}")
                await self._page.goto(page_url, wait_until="domcontentloaded")
                await self._delay()
                await self._scroll_to_bottom()

                items = await self._page.query_selector_all(".item-cell")
                logger.info(f"[{self.retailer_name}] Found {len(items)} raw items on page {page_num}")

                if not items:
                    break

                page_new = 0
                for item in items:
                    try:
                        raw = await self._extract_combo_item(item)
                        if raw and raw.get("url", "") not in seen_urls:
                            seen_urls.add(raw["url"])
                            all_raw_items.append(raw)
                            page_new += 1
                    except Exception as e:
                        logger.warning(f"[{self.retailer_name}] Failed to extract item: {e}")

                if page_new == 0:
                    break

        logger.info(f"[{self.retailer_name}] Collected {len(all_raw_items)} raw items from {len(NEWEGG_SEARCH_URLS)} queries")

        # Phase 2: Parse items and visit detail pages for incomplete combos.
        # Now it's safe to navigate because we no longer hold element handles.
        deals = []
        for raw in all_raw_items:
            deal = parse_combo_item(raw)
            if deal.combo_type == "OTHER":
                logger.debug(f"[{self.retailer_name}] Skipped OTHER: {raw.get('title', '')[:80]}")
                continue

            # Fallback: if combo URL detected but components are incomplete,
            # visit the detail page to get full component info
            categories = {c.category for c in deal.components}
            is_combo_url = "ComboDealDetails" in deal.url
            if is_combo_url and len(categories - {"unknown"}) < 3:
                logger.info(f"[{self.retailer_name}] Incomplete components ({categories}), "
                            f"fetching detail page: {deal.url}")
                detail_deal = await self._scrape_combo_detail(deal.url)
                if detail_deal and detail_deal.combo_type != "OTHER":
                    deal = detail_deal

            if deal.combo_type != "OTHER":
                deals.append(deal)

        logger.info(f"[{self.retailer_name}] Total deals: {len(deals)}")
        return deals

    async def _scrape_combo_detail(self, url: str) -> ComboDeal | None:
        """Visit a combo deal detail page to extract full component info."""
        try:
            await self._page.goto(url, wait_until="domcontentloaded")
            await self._delay()

            # Extract product names from combo item elements.
            # Newegg combo pages list each product as a link with the product title.
            # Try multiple selector strategies.
            product_names = []

            # Strategy 1: Find product links within combo item containers
            for selector in [".combo-item-info a", ".product-title", ".item-info a"]:
                els = await self._page.query_selector_all(selector)
                if els:
                    for el in els:
                        text = (await el.inner_text()).strip()
                        if text and len(text) > 10 and _detect_category(text) != "unknown":
                            product_names.append(text)
                    if product_names:
                        break

            # Strategy 2: Find all links to Newegg product pages
            if not product_names:
                links = await self._page.query_selector_all("a[href*='/p/N82E']")
                for link in links:
                    text = (await link.inner_text()).strip()
                    if text and len(text) > 10 and _detect_category(text) != "unknown":
                        product_names.append(text)

            # Strategy 3: Extract from page text using category keyword matching
            if not product_names:
                body_text = await self._page.inner_text("body")
                # Split by newlines and look for lines that match component categories
                for line in body_text.split("\n"):
                    line = line.strip()
                    if 15 < len(line) < 200 and _detect_category(line) != "unknown":
                        # Avoid navigation/footer text by requiring a brand-like pattern
                        if any(brand in line.lower() for brand in [
                            "amd", "intel", "asus", "msi", "gigabyte", "asrock",
                            "corsair", "g.skill", "gskill", "kingston", "crucial",
                            "patriot", "v-color", "team", "trident",
                        ]):
                            product_names.append(line)

            if not product_names:
                logger.warning(f"[{self.retailer_name}] Could not extract components from {url}")
                return None

            # Deduplicate while preserving order
            seen = set()
            unique_names = []
            for name in product_names:
                key = name.lower()[:40]
                if key not in seen:
                    seen.add(key)
                    unique_names.append(name)

            components = []
            for name in unique_names:
                category = _detect_category(name)
                components.append({"name": name, "category": category})

            # Get price from the detail page
            price_text = ""
            price_el = await self._page.query_selector(".price-current, .combo-price, [class*='price'] strong")
            if price_el:
                price_text = (await price_el.inner_text()).strip()

            raw = {"title": " + ".join(unique_names), "price": price_text, "url": url, "components": components}
            deal = parse_combo_item(raw)
            logger.info(f"[{self.retailer_name}] Detail page extracted: {deal.combo_type} "
                        f"({len(components)} components) from {url}")
            return deal

        except Exception as e:
            logger.warning(f"[{self.retailer_name}] Failed to scrape detail page {url}: {e}")
            return None

    async def _extract_combo_item(self, element) -> dict | None:
        """Extract raw combo deal data from a page element."""
        title_el = await element.query_selector(".item-title")
        price_el = await element.query_selector(".price-current")

        if not title_el or not price_el:
            return None

        title = (await title_el.inner_text()).strip()
        price_text = (await price_el.inner_text()).strip()
        url = await title_el.get_attribute("href") or ""

        # Extract category order from prefix before stripping it.
        # e.g. "CPU Motherboard Memory Combo" → ["cpu", "motherboard", "ram"]
        prefix_categories = _extract_prefix_categories(title)

        # Strip combo title prefixes in any word order
        clean_title = re.sub(
            r"^(?:CPU|Motherboard|Memory|Combo|Bundle)(?:\s+(?:CPU|Motherboard|Memory|Combo|Bundle))*\s*[-–—]\s*",
            "", title, flags=re.IGNORECASE,
        )

        # Split components by " + ", " Bundle with ", " and ", " with ", or ","
        comp_names = re.split(r"\s+Bundle\s+with\s+|\s+(?:\+|and|with)\s+|,\s*", clean_title)
        components = []
        for i, name in enumerate(comp_names):
            name = re.sub(r"\s+Bundle$", "", name.strip(), flags=re.IGNORECASE)
            if name and len(name) > 3:
                # Use prefix category if available and keyword detection fails
                category = _detect_category(name)
                if category == "unknown" and i < len(prefix_categories):
                    category = prefix_categories[i]
                components.append({"name": name, "category": category})

        if not components:
            return None

        return {
            "title": title,
            "price": price_text,
            "url": url,
            "components": components,
        }
