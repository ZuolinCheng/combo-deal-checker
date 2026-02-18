"""Discord webhook notifications for new deals."""
import json
import logging
import os
import subprocess
import urllib.request
from datetime import datetime

from models import ComboDeal

logger = logging.getLogger(__name__)

SEEN_DEALS_FILE = os.path.join("cache", "seen_deals.json")


def load_seen_urls() -> set[str]:
    """Load previously-notified deal URLs from disk."""
    if not os.path.exists(SEEN_DEALS_FILE):
        return set()
    try:
        with open(SEEN_DEALS_FILE, "r") as f:
            return set(json.load(f))
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
    new_deals = [d for d in deals if d.url and d.url not in seen_urls]

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

    # Mark all new deals as seen
    for deal in new_deals:
        seen_urls.add(deal.url)
    _save_seen_urls(seen_urls)

    return len(new_deals)


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
