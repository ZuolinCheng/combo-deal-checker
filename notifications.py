"""Discord webhook notifications for new deals."""
import json
import logging
import os
import re
import subprocess
import urllib.request
from datetime import datetime

from models import ComboDeal

logger = logging.getLogger(__name__)

_AMAZON_ASIN_RE = re.compile(r"/dp/([A-Z0-9]{10})")


def normalize_url(url: str) -> str:
    """Normalize a deal URL to a stable canonical form.

    Amazon search-result URLs contain volatile query params (qid, dib, sr)
    that change every request.  Collapse them to ``/dp/{ASIN}`` so the same
    product isn't treated as a different deal on every scrape run.
    """
    if "amazon.com" in url:
        m = _AMAZON_ASIN_RE.search(url)
        if m:
            return f"https://www.amazon.com/dp/{m.group(1)}"
    return url

SEEN_DEALS_FILE = os.path.join("cache", "seen_deals.json")


def load_seen_urls() -> set[str]:
    """Load previously-notified deal URLs from disk (normalized)."""
    if not os.path.exists(SEEN_DEALS_FILE):
        return set()
    try:
        with open(SEEN_DEALS_FILE, "r") as f:
            return {normalize_url(u) for u in json.load(f)}
    except (json.JSONDecodeError, OSError):
        return set()


def _save_seen_urls(urls: set[str]):
    """Persist seen deal URLs to disk."""
    os.makedirs(os.path.dirname(SEEN_DEALS_FILE), exist_ok=True)
    with open(SEEN_DEALS_FILE, "w") as f:
        json.dump(sorted(urls), f, indent=2)


def _format_deal_embed(deal: ComboDeal) -> dict:
    """Format a single deal as a Discord embed object."""
    # Build component list
    parts = []
    if deal.cpu_name:
        parts.append(f"**CPU:** {deal.cpu_name} ({deal.cpu_cores})")
    if deal.motherboard_name:
        parts.append(f"**MB:** {deal.motherboard_name}")
    if deal.ram_name:
        ram_info = deal.ram_name
        if deal.ram_capacity_gb:
            ram_info += f" ({deal.ram_capacity_gb}GB"
            if deal.ram_speed_mhz:
                ram_info += f" @ {deal.ram_speed_mhz}MHz"
            ram_info += ")"
        parts.append(f"**RAM:** {ram_info}")

    description = "\n".join(parts)

    # Price info
    price_line = f"**Combo Price:** ${deal.combo_price:.2f}"
    if deal.savings > 0:
        price_line += f"  |  **Save ${deal.savings:.2f}** ({deal.savings_percent():.0f}%)"
    description += f"\n\n{price_line}"

    # CPU benchmark
    if deal.cpu_sc_score:
        description += f"\n**Benchmark:** SC {deal.cpu_sc_score} / MC {deal.cpu_mc_score}"

    return {
        "title": f"[{deal.retailer}] {deal.combo_type} — ${deal.combo_price:.0f}",
        "description": description,
        "url": deal.url,
        "color": 0x57F287,  # green
        "footer": {"text": f"Found {datetime.now().strftime('%Y-%m-%d %H:%M')}"},
    }


def send_discord_notifications(deals: list[ComboDeal], webhook_url: str) -> int:
    """Send Discord notifications for new (unseen) deals.

    Returns the number of new deals notified.
    """
    if not webhook_url:
        logger.warning("No Discord webhook URL configured — skipping notifications")
        return 0

    seen_urls = load_seen_urls()
    new_deals = [d for d in deals if d.url and normalize_url(d.url) not in seen_urls]

    if not new_deals:
        logger.info("No new deals to notify about")
        return 0

    logger.info(f"Sending Discord notifications for {len(new_deals)} new deal(s)")

    # Discord allows max 10 embeds per message — batch if needed
    for i in range(0, len(new_deals), 10):
        batch = new_deals[i : i + 10]
        embeds = [_format_deal_embed(d) for d in batch]

        payload = {
            "content": f"**🔔 {len(new_deals)} New Combo Deal(s) Found!**" if i == 0 else None,
            "embeds": embeds,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ComboDealChecker/1.0",
            },
        )

        try:
            with urllib.request.urlopen(req) as resp:
                if resp.status == 204:
                    logger.info(f"Discord batch {i // 10 + 1}: sent {len(batch)} embeds")
                else:
                    logger.warning(f"Discord responded with status {resp.status}")
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return 0

    # Mark all new deals as seen (normalized)
    for deal in new_deals:
        seen_urls.add(normalize_url(deal.url))
    _save_seen_urls(seen_urls)

    return len(new_deals)


def _format_ram_deal_embed(deal) -> dict:
    """Format a standalone RAM deal as a Discord embed object."""
    from display_names import shorten_ram

    description = f"**RAM:** {shorten_ram(deal.name)}"
    description += f"\n**Capacity:** {deal.capacity_gb}GB"
    if deal.speed_mhz:
        description += f" @ {deal.speed_mhz}MHz"

    price_line = f"\n\n**Price:** ${deal.price:.2f}"
    if deal.amazon_price > 0:
        price_line += f"  |  **Amazon:** ${deal.amazon_price:.2f}"
    if deal.savings > 0:
        price_line += f"  |  **Save ${deal.savings:.2f}**"
    description += price_line

    return {
        "title": f"[{deal.retailer}] {deal.capacity_gb}GB DDR5 RAM — ${deal.price:.0f}",
        "description": description,
        "url": deal.url,
        "color": 0xE040FB,  # magenta
        "footer": {"text": f"Found {datetime.now().strftime('%Y-%m-%d %H:%M')}"},
    }


def send_ram_discord_notifications(deals: list, webhook_url: str) -> int:
    """Send Discord notifications for new (unseen) standalone RAM deals.

    Returns the number of new deals notified.
    """
    if not webhook_url:
        return 0

    seen_urls = load_seen_urls()
    new_deals = [d for d in deals if d.url and normalize_url(d.url) not in seen_urls]

    if not new_deals:
        logger.info("No new RAM deals to notify about")
        return 0

    logger.info(f"Sending Discord notifications for {len(new_deals)} new RAM deal(s)")

    for i in range(0, len(new_deals), 10):
        batch = new_deals[i:i + 10]
        embeds = [_format_ram_deal_embed(d) for d in batch]

        payload = {
            "content": f"**\U0001f9e0 {len(new_deals)} New DDR5 RAM Deal(s) Found!**" if i == 0 else None,
            "embeds": embeds,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ComboDealChecker/1.0",
            },
        )

        try:
            with urllib.request.urlopen(req) as resp:
                if resp.status == 204:
                    logger.info(f"Discord RAM batch {i // 10 + 1}: sent {len(batch)} embeds")
                else:
                    logger.warning(f"Discord responded with status {resp.status}")
        except Exception as e:
            logger.error(f"Failed to send Discord RAM notification: {e}")
            return 0

    for deal in new_deals:
        seen_urls.add(normalize_url(deal.url))
    _save_seen_urls(seen_urls)

    return len(new_deals)


def _retailer_from_url(url: str) -> str:
    """Guess retailer name from a deal URL."""
    if "newegg.com" in url:
        return "Newegg"
    if "amazon.com" in url:
        return "Amazon"
    if "microcenter.com" in url:
        return "Micro Center"
    if "bhphotovideo.com" in url:
        return "B&H Photo"
    return "Unknown"


def _format_expired_embed(url: str, reason: str) -> dict:
    """Format an expired/OOS deal as a Discord embed."""
    retailer = _retailer_from_url(url)
    return {
        "title": f"[{retailer}] Deal {reason}",
        "description": url,
        "url": url,
        "color": 0xED4245,  # red
        "footer": {"text": f"Detected {datetime.now().strftime('%Y-%m-%d %H:%M')}"},
    }


def _format_expired_deal_embed(deal: ComboDeal) -> dict:
    """Format an OOS combo deal with component details as a Discord embed."""
    parts = []
    if deal.cpu_name:
        parts.append(f"**CPU:** {deal.cpu_name}")
    if deal.motherboard_name:
        parts.append(f"**MB:** {deal.motherboard_name}")
    if deal.ram_name:
        parts.append(f"**RAM:** {deal.ram_name}")
    description = "\n".join(parts) if parts else deal.url
    description += f"\n\n**Last price:** ${deal.combo_price:.2f}"

    return {
        "title": f"[{deal.retailer}] {deal.combo_type} — OUT OF STOCK",
        "description": description,
        "url": deal.url,
        "color": 0xED4245,  # red
        "footer": {"text": f"Detected {datetime.now().strftime('%Y-%m-%d %H:%M')}"},
    }


def _send_webhook(webhook_url: str, payload: dict) -> bool:
    """Send a single webhook payload. Returns True on success."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "ComboDealChecker/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status == 204
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")
        return False


def find_expired_deals(
    all_deals: list[ComboDeal],
    all_ram_deals: list,
    seen_urls: set[str],
    scraper_results: dict,
) -> tuple[list[ComboDeal], set[str]]:
    """Identify deals that went OOS or disappeared since last run.

    Returns:
        (oos_deals, disappeared_urls) — OOS deals have full ComboDeal data,
        disappeared URLs are bare strings for deals no longer in any scraper result.
    """
    # All URLs scraped this run (regardless of filtering), normalized
    current_urls = {normalize_url(d.url) for d in all_deals if d.url}
    current_urls.update(normalize_url(d.url) for d in all_ram_deals if d.url)

    # OOS combo deals that were previously notified about
    oos_deals = [d for d in all_deals if not d.in_stock and d.url in seen_urls]

    # Disappeared: in seen_urls but not scraped at all this run.
    # Only flag if the corresponding retailer's scraper succeeded.
    ok_scrapers = {name for name, r in scraper_results.items() if r["status"] == "ok"}
    retailer_domain_map = {
        "newegg.com": ["NeweggScraper", "RAM-NeweggRAMScraper"],
        "amazon.com": ["AmazonScraper", "RAM-AmazonRAMScraper"],
        "microcenter.com": ["MicroCenterScraper", "RAM-MicroCenterRAMScraper"],
        "bhphotovideo.com": ["BHPhotoScraper", "RAM-BHPhotoRAMScraper"],
    }

    disappeared_urls: set[str] = set()
    for url in seen_urls:
        if url in current_urls:
            continue
        for domain, scraper_names in retailer_domain_map.items():
            if domain in url and any(s in ok_scrapers for s in scraper_names):
                disappeared_urls.add(url)
                break

    return oos_deals, disappeared_urls


def send_discord_expired_notifications(
    oos_deals: list[ComboDeal],
    disappeared_urls: set[str],
    webhook_url: str,
) -> int:
    """Send Discord notifications for expired (OOS/disappeared) deals.

    Returns total number of expired deals notified.
    """
    if not webhook_url:
        return 0

    total = len(oos_deals) + len(disappeared_urls)
    if total == 0:
        logger.info("No expired deals to notify about")
        return 0

    logger.info(f"Sending Discord notifications for {total} expired deal(s) "
                f"({len(oos_deals)} OOS, {len(disappeared_urls)} disappeared)")

    embeds = [_format_expired_deal_embed(d) for d in oos_deals]
    embeds += [_format_expired_embed(url, "no longer listed") for url in sorted(disappeared_urls)]

    for i in range(0, len(embeds), 10):
        batch = embeds[i:i + 10]
        payload = {
            "content": f"**\u274c {total} Deal(s) Expired**" if i == 0 else None,
            "embeds": batch,
        }
        if not _send_webhook(webhook_url, payload):
            return 0

    # Remove expired URLs from seen set so they don't re-trigger
    seen_urls = load_seen_urls()
    for deal in oos_deals:
        seen_urls.discard(deal.url)
    seen_urls -= disappeared_urls
    _save_seen_urls(seen_urls)

    return total


def send_discord_file(filepath: str, webhook_url: str, message: str = "") -> bool:
    """Upload a file to Discord via webhook using curl.

    Returns True on success.
    """
    if not webhook_url:
        logger.warning("No Discord webhook URL configured — skipping file upload")
        return False

    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        return False

    cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}"]
    if message:
        cmd += ["-F", f'payload_json={{"content":"{message}"}}']
    cmd += ["-F", f"file=@{filepath}", webhook_url]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.stdout.strip() == "200":
            logger.info(f"Discord file upload: sent {os.path.basename(filepath)}")
            return True
        else:
            logger.warning(f"Discord file upload failed with status {result.stdout.strip()}")
            return False
    except Exception as e:
        logger.error(f"Failed to upload file to Discord: {e}")
        return False
